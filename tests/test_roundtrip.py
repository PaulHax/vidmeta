"""Test round-trip metadata preservation and lossless video modification."""

import hashlib
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import cv2
import pytest

from vidmeta.video_modifier import modify_video_metadata, parse_klv_file


@pytest.fixture(scope="module")
def sample_video():
    """Download sample video once for all tests."""
    videos_dir = Path("videos")
    videos_dir.mkdir(exist_ok=True)

    video_file = videos_dir / "sample_video.mpg"

    if not video_file.exists():
        download_url = (
            "https://data.kitware.com/api/v1/file/604a5a532fa25629b931c673/download"
        )
        urllib.request.urlretrieve(download_url, video_file)

    return str(video_file)


def test_roundtrip_preserves_metadata(sample_video, tmp_path):
    """Test that round-trip preserves all metadata correctly."""
    output_video = tmp_path / "roundtrip_test.ts"

    # Run lossless modification with no overrides
    result = modify_video_metadata(
        input_video_path=sample_video,
        output_video_path=str(output_video),
        metadata_overrides={},
        lossless=True,
    )

    assert result["success"]
    assert Path(result["video_path"]).exists()
    assert Path(result["klv_path"]).exists()

    # Extract original KLV for comparison
    temp_klv = tempfile.mktemp(suffix=".klv")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        sample_video,
        "-map",
        "0:d",
        "-c",
        "copy",
        "-f",
        "data",
        temp_klv,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    original_metadata = parse_klv_file(temp_klv)
    roundtrip_metadata = parse_klv_file(result["klv_path"])

    # Check we have metadata
    assert len(original_metadata) > 0
    assert len(roundtrip_metadata) > 0

    # Round-trip should have metadata for all video frames
    assert result["num_frames"] == len(roundtrip_metadata)

    # Compare metadata for several frames
    frames_to_check = [0, 100, 500, 1000]

    for frame_num in frames_to_check:
        if frame_num >= len(roundtrip_metadata):
            continue

        # Unpack tuples (metadata_dict, raw_packet, unknown_tags)
        orig_tuple = original_metadata.get(frame_num, ({}, None, {}))
        trip_tuple = roundtrip_metadata.get(frame_num, ({}, None, {}))

        # Extract just the metadata dicts
        if isinstance(orig_tuple, tuple):
            if len(orig_tuple) >= 3:
                orig, _, _ = orig_tuple[0], orig_tuple[1], orig_tuple[2]
            elif len(orig_tuple) == 2:
                orig, _ = orig_tuple
            else:
                orig = orig_tuple[0]
        else:
            orig = orig_tuple

        if isinstance(trip_tuple, tuple):
            if len(trip_tuple) >= 3:
                trip, _, _ = trip_tuple[0], trip_tuple[1], trip_tuple[2]
            elif len(trip_tuple) == 2:
                trip, _ = trip_tuple
            else:
                trip = trip_tuple[0]
        else:
            trip = trip_tuple

        # Check all keys are preserved
        assert orig.keys() == trip.keys(), f"Frame {frame_num}: key mismatch"

        # Check all values match (within tolerance for floats)
        for key in orig.keys():
            orig_val = orig[key]
            trip_val = trip[key]

            if isinstance(orig_val, (int, float)) and isinstance(
                trip_val, (int, float)
            ):
                # Allow 0.1% tolerance for floating point rounding
                if abs(orig_val) > 0:
                    rel_diff = abs(orig_val - trip_val) / abs(orig_val)
                    assert rel_diff < 0.001, (
                        f"Frame {frame_num}, {key}: {orig_val} != {trip_val} (diff: {rel_diff * 100:.3f}%)"
                    )
                else:
                    assert abs(orig_val - trip_val) < 1e-6
            else:
                assert orig_val == trip_val, (
                    f"Frame {frame_num}, {key}: {orig_val} != {trip_val}"
                )

    # Cleanup
    Path(temp_klv).unlink()


def test_roundtrip_frame_count_matches(sample_video, tmp_path):
    """Test that output has same number of frames as input."""
    output_video = tmp_path / "roundtrip_frames.ts"

    result = modify_video_metadata(
        input_video_path=sample_video,
        output_video_path=str(output_video),
        metadata_overrides={},
        lossless=True,
    )

    # Count frames in original
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-count_packets",
        "-show_entries",
        "stream=nb_read_packets",
        "-of",
        "csv=p=0",
        sample_video,
    ]
    original_frames = int(subprocess.check_output(cmd).decode().strip().split()[0])

    # Count frames in output
    cmd[cmd.index(sample_video)] = str(output_video)
    output_frames = int(subprocess.check_output(cmd).decode().strip().split()[0])

    assert output_frames == original_frames
    assert result["num_frames"] == original_frames


def test_modification_with_overrides(sample_video, tmp_path):
    """Test that metadata overrides are applied correctly."""
    output_video = tmp_path / "modified_test.ts"

    # Modify latitude and longitude on frame 0
    metadata_overrides = {
        0: {"latitude": 37.7749, "longitude": -122.4194},
    }

    result = modify_video_metadata(
        input_video_path=sample_video,
        output_video_path=str(output_video),
        metadata_overrides=metadata_overrides,
        lossless=True,
    )

    assert result["success"]

    # Parse output metadata
    output_metadata = parse_klv_file(result["klv_path"])

    # Check frame 0 has the new values
    # Unpack tuple (metadata_dict, raw_packet, unknown_tags)
    frame_0_tuple = output_metadata[0]
    if isinstance(frame_0_tuple, tuple):
        if len(frame_0_tuple) >= 3:
            frame_0 = frame_0_tuple[0]
        elif len(frame_0_tuple) == 2:
            frame_0 = frame_0_tuple[0]
        else:
            frame_0 = frame_0_tuple[0]
    else:
        frame_0 = frame_0_tuple

    assert abs(frame_0["latitude"] - 37.7749) < 0.01
    assert abs(frame_0["longitude"] - (-122.4194)) < 0.01

    # Check other fields are preserved
    assert "altitude" in frame_0
    assert "heading" in frame_0
    assert "timestamp" in frame_0


def test_multiple_frame_modifications(sample_video, tmp_path):
    """Test modifying multiple frames."""
    output_video = tmp_path / "multi_modified.ts"

    metadata_overrides = {
        0: {"latitude": 40.0},
        5: {"heading": 180.0},
        10: {"altitude": 2000.0},
    }

    result = modify_video_metadata(
        input_video_path=sample_video,
        output_video_path=str(output_video),
        metadata_overrides=metadata_overrides,
        lossless=True,
    )

    output_metadata = parse_klv_file(result["klv_path"])

    # Helper to unpack tuples (handles 2 or 3 element tuples)
    def get_metadata(frame_tuple):
        if isinstance(frame_tuple, tuple) and len(frame_tuple) > 0:
            return frame_tuple[0]
        return frame_tuple

    # Check each modified frame (allow 0.1 tolerance for KLV encoding precision)
    assert abs(get_metadata(output_metadata[0])["latitude"] - 40.0) < 0.1
    assert abs(get_metadata(output_metadata[5])["heading"] - 180.0) < 0.1
    assert abs(get_metadata(output_metadata[10])["altitude"] - 2000.0) < 0.1

    # Check unmodified frames still have original metadata
    assert "longitude" in get_metadata(output_metadata[0])  # Not modified
    assert "pitch" in get_metadata(output_metadata[5])  # Not modified
    assert "latitude" in get_metadata(output_metadata[10])  # Not modified


def extract_frame_hashes(video_path: str, frame_indices: list) -> dict:
    """Extract MD5 hashes of specific frames from a video."""
    cap = cv2.VideoCapture(video_path)
    hashes = {}

    for frame_idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            hashes[frame_idx] = hashlib.md5(frame.tobytes()).hexdigest()

    cap.release()
    return hashes


def test_lossless_preserves_video_frames(sample_video, tmp_path):
    """Test that lossless mode preserves video frames exactly (bitwise identical)."""
    output_video = tmp_path / "lossless_test.mpg"

    # Modify some metadata (use valid MISB ranges: latitude -90 to 90)
    metadata_overrides = {
        0: {"latitude": 45.0},
        100: {"heading": 270.0},
    }

    result = modify_video_metadata(
        input_video_path=sample_video,
        output_video_path=str(output_video),
        metadata_overrides=metadata_overrides,
        lossless=True,
    )

    assert result["success"]
    assert result.get("lossless") is True

    # Extract frame hashes from original and output
    frames_to_check = [0, 50, 100, 500, 1000, 1500]

    original_hashes = extract_frame_hashes(sample_video, frames_to_check)
    output_hashes = extract_frame_hashes(str(output_video), frames_to_check)

    # All frame hashes should be identical
    for frame_idx in frames_to_check:
        if frame_idx in original_hashes and frame_idx in output_hashes:
            assert original_hashes[frame_idx] == output_hashes[frame_idx], (
                f"Frame {frame_idx} differs: lossless mode should preserve frames exactly"
            )


def test_lossless_output_mpg_extension(sample_video, tmp_path):
    """Test that .mpg output extension works."""
    output_video = tmp_path / "output_test.mpg"

    result = modify_video_metadata(
        input_video_path=sample_video,
        output_video_path=str(output_video),
        metadata_overrides={0: {"latitude": 42.0}},
        lossless=True,
    )

    assert result["success"]
    assert output_video.exists()
    assert output_video.suffix == ".mpg"

    # Verify output is valid MPEG-TS
    cmd = ["ffprobe", "-v", "error", "-show_format", str(output_video)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "mpegts" in proc.stdout


def test_re_encode_mode_still_works(sample_video, tmp_path):
    """Test that re-encode mode (lossless=False) still works."""
    output_video = tmp_path / "re_encode_test.ts"

    result = modify_video_metadata(
        input_video_path=sample_video,
        output_video_path=str(output_video),
        metadata_overrides={0: {"latitude": 55.0}},
        lossless=False,
        backend="gstreamer",
    )

    assert result["success"]
    assert output_video.exists()

    # In re-encode mode, lossless should not be set
    assert result.get("lossless") is not True

    # Verify metadata was modified
    output_metadata = parse_klv_file(result["klv_path"])

    def get_metadata(frame_tuple):
        if isinstance(frame_tuple, tuple) and len(frame_tuple) > 0:
            return frame_tuple[0]
        return frame_tuple

    assert abs(get_metadata(output_metadata[0])["latitude"] - 55.0) < 0.1


def test_lossless_preserves_all_frames(sample_video, tmp_path):
    """Test that lossless mode preserves ALL video frames (comprehensive check)."""
    output_video = tmp_path / "lossless_all_frames_test.mpg"

    # Modify metadata on multiple frames (use valid MISB ranges)
    result = modify_video_metadata(
        input_video_path=sample_video,
        output_video_path=str(output_video),
        metadata_overrides={0: {"latitude": 42.0}, 500: {"heading": 123.0}},
        lossless=True,
    )

    assert result["success"]

    # Open both videos
    cap_original = cv2.VideoCapture(sample_video)
    cap_output = cv2.VideoCapture(str(output_video))

    original_frame_count = int(cap_original.get(cv2.CAP_PROP_FRAME_COUNT))
    output_frame_count = int(cap_output.get(cv2.CAP_PROP_FRAME_COUNT))

    assert original_frame_count == output_frame_count, (
        f"Frame count mismatch: {original_frame_count} vs {output_frame_count}"
    )

    # Check every 100th frame to verify lossless preservation
    frames_checked = 0
    frames_matched = 0

    for frame_idx in range(0, min(original_frame_count, output_frame_count), 100):
        cap_original.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        cap_output.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        ret1, frame1 = cap_original.read()
        ret2, frame2 = cap_output.read()

        if ret1 and ret2:
            frames_checked += 1
            hash1 = hashlib.md5(frame1.tobytes()).hexdigest()
            hash2 = hashlib.md5(frame2.tobytes()).hexdigest()
            if hash1 == hash2:
                frames_matched += 1

    cap_original.release()
    cap_output.release()

    # All checked frames should match
    assert frames_checked > 0, "No frames were checked"
    assert frames_matched == frames_checked, (
        f"Only {frames_matched}/{frames_checked} frames matched - "
        "lossless mode should preserve all frames exactly"
    )
