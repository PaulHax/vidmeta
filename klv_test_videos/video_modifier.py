"""Modify KLV metadata in existing videos."""

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import cv2
import numpy as np

try:
    from klvdata import misb0601

    KLVDATA_AVAILABLE = True
except ImportError:
    KLVDATA_AVAILABLE = False

from .video_builder import build_klv_video, VideoFrameGenerator


def parse_klv_packet(packet: bytes) -> Dict[str, Any]:
    """
    Parse a KLV packet into a metadata dictionary.

    Args:
        packet: Raw KLV packet bytes

    Returns:
        Dictionary with metadata fields
    """
    if not KLVDATA_AVAILABLE:
        raise ImportError("klvdata library required for parsing KLV packets")

    # Parse using klvdata
    uas_set = misb0601.UASLocalMetadataSet(packet)
    metadata_dict = uas_set.MetadataList()

    # Convert klvdata metadata dict to our dict format
    # MetadataList() returns OrderedDict with {tag_num: (name, long_name, unit, value_str)}
    metadata = {}

    # Store the raw packet for pass-through of all fields
    metadata["_raw_klv_packet"] = packet

    for tag_num, tag_info in metadata_dict.items():
        name = tag_info[0]  # First element is the name
        value_str = tag_info[3]  # Fourth element is the value as string

        # Map klvdata names to our metadata keys
        # Most values are numeric strings, some are text
        if name == "Precision Time Stamp" or name == "Event Start Time - UTC":
            # Parse timestamp string (format: ISO 8601 datetime string)
            try:
                # klvdata returns ISO format like '2015-10-07 07:18:02.380305+00:00'
                metadata["timestamp"] = datetime.fromisoformat(value_str)
            except (ValueError, OSError):
                # If parsing fails, keep as string
                metadata["timestamp"] = value_str
        elif name == "Mission ID":
            metadata["mission_id"] = value_str
        elif name == "Platform Designation":
            metadata["platform_designation"] = value_str
        elif name == "Platform Call Sign":
            metadata["platform_call_sign"] = value_str
        elif name == "Platform Tail Number":
            metadata["platform_tail_number"] = value_str
        elif name == "Image Source Sensor":
            metadata["sensor_name"] = value_str
        elif name == "Sensor Latitude":
            metadata["latitude"] = float(value_str)
        elif name == "Sensor Longitude":
            metadata["longitude"] = float(value_str)
        elif name == "Sensor True Altitude":
            metadata["altitude"] = float(value_str)
        elif name == "Platform Heading Angle":
            metadata["heading"] = float(value_str)
        elif name == "Platform Pitch Angle":
            metadata["pitch"] = float(value_str)
        elif name == "Platform Roll Angle":
            metadata["roll"] = float(value_str)
        elif name == "Sensor Relative Azimuth Angle":
            metadata["sensor_relative_azimuth"] = float(value_str)
        elif name == "Sensor Relative Elevation Angle":
            metadata["sensor_relative_elevation"] = float(value_str)
        elif name == "Sensor Relative Roll Angle":
            metadata["sensor_relative_roll"] = float(value_str)
        elif name == "Sensor Horizontal Field of View":
            metadata["horizontal_fov"] = float(value_str)
        elif name == "Sensor Vertical Field of View":
            metadata["vertical_fov"] = float(value_str)
        elif name == "Slant Range":
            metadata["slant_range"] = float(value_str)
        elif name == "Target Width":
            metadata["target_width"] = float(value_str)
        elif name == "Ground Range":
            metadata["ground_range"] = float(value_str)
        elif name == "Platform Ground Speed":
            metadata["platform_ground_speed"] = float(value_str)
        elif name == "Frame Center Latitude":
            metadata["frame_center_latitude"] = float(value_str)
        elif name == "Frame Center Longitude":
            metadata["frame_center_longitude"] = float(value_str)
        elif name == "Frame Center Elevation":
            metadata["frame_center_elevation"] = float(value_str)
        elif name == "UAS Datalink LS Version Number":
            metadata["version"] = int(float(value_str))

    return metadata


def extract_klv_stream_ffmpeg(video_path: str, output_path: str) -> None:
    """
    Extract KLV/data stream from video using FFmpeg.

    Args:
        video_path: Path to input video
        output_path: Path to save extracted KLV data
    """
    # Use FFmpeg to extract the data stream (KLV)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-map",
        "0:d",  # Map data stream
        "-c",
        "copy",  # Copy without re-encoding
        "-f",
        "data",  # Output as raw data
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed to extract KLV stream: {result.stderr}")


def parse_klv_file(klv_path: str) -> Dict[int, Dict[str, Any]]:
    """
    Parse KLV packets from a file into frame-indexed metadata.

    Args:
        klv_path: Path to file containing raw KLV packets

    Returns:
        Dictionary mapping frame numbers to metadata dicts
    """
    metadata_per_frame = {}

    with open(klv_path, "rb") as f:
        klv_data = f.read()

    # UAS LS key is 16 bytes
    uas_ls_key = bytes(
        [
            0x06,
            0x0E,
            0x2B,
            0x34,
            0x02,
            0x0B,
            0x01,
            0x01,
            0x0E,
            0x01,
            0x03,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
        ]
    )

    frame_num = 0
    offset = 0

    while offset < len(klv_data):
        # Find next UAS LS key
        key_start = klv_data.find(uas_ls_key, offset)
        if key_start == -1:
            break

        # Read BER-encoded length
        offset = key_start + 16
        if offset >= len(klv_data):
            break

        length_byte = klv_data[offset]
        if length_byte & 0x80:
            # Multi-byte length
            num_length_bytes = length_byte & 0x7F
            if offset + num_length_bytes >= len(klv_data):
                break
            length = int.from_bytes(
                klv_data[offset + 1 : offset + 1 + num_length_bytes], "big"
            )
            offset += 1 + num_length_bytes
        else:
            length = length_byte
            offset += 1

        # Extract packet value (without key and length prefix)
        if offset + length > len(klv_data):
            break

        # Pass only the value portion to the parser (not the key/length prefix)
        packet_value = klv_data[offset : offset + length]

        # Parse packet
        try:
            metadata = parse_klv_packet(packet_value)
            metadata_per_frame[frame_num] = metadata
            frame_num += 1
        except Exception as e:
            print(f"Warning: Failed to parse packet at frame {frame_num}: {e}")

        offset += length

    return metadata_per_frame


def extract_video_frames(video_path: str) -> List[np.ndarray]:
    """
    Extract all frames from video.

    Args:
        video_path: Path to video file

    Returns:
        List of frames as numpy arrays (BGR format)
    """
    cap = cv2.VideoCapture(video_path)
    frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)

    cap.release()
    return frames


def modify_video_metadata(
    input_video_path: str,
    output_video_path: str,
    metadata_overrides: Dict[int, Dict[str, Any]],
    backend: str = "gstreamer",
) -> Dict[str, Any]:
    """
    Modify KLV metadata in an existing video.

    Takes an existing video with KLV metadata and produces a new video with modified
    metadata. Original video frames are preserved. Metadata for frames not in
    metadata_overrides is kept unchanged. Fields in metadata_overrides are merged
    with existing metadata (add/update specified fields only).

    Args:
        input_video_path: Path to input video with KLV metadata
        output_video_path: Path for output video
        metadata_overrides: Dict mapping frame numbers to metadata field updates
                           Example: {5: {"latitude": 37.5}, 10: {"altitude": 1000}}
        backend: "gstreamer" (default) or "ffmpeg"

    Returns:
        Dictionary with generation results from build_klv_video()

    Raises:
        ValueError: If frame numbers in metadata_overrides exceed video length
        ImportError: If klvdata library not available for parsing
        RuntimeError: If FFmpeg fails to extract KLV stream

    Example:
        >>> metadata_overrides = {
        ...     0: {"latitude": 37.7749},
        ...     5: {"heading": 180.0},
        ...     10: {"altitude": 2000.0, "pitch": -20.0}
        ... }
        >>> result = modify_video_metadata(
        ...     "input.mpg", "output.ts", metadata_overrides
        ... )
    """
    print(f"Processing {input_video_path}...")

    # Extract KLV stream using FFmpeg
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_klv = Path(temp_dir) / "extracted.klv"

        print("Extracting KLV stream with FFmpeg...")
        extract_klv_stream_ffmpeg(input_video_path, str(temp_klv))

        print("Parsing KLV metadata...")
        original_metadata = parse_klv_file(str(temp_klv))

    print(f"Found metadata for {len(original_metadata)} frames")

    print("Extracting video frames...")
    frames = extract_video_frames(input_video_path)
    num_frames = len(frames)
    print(f"Extracted {num_frames} frames")

    # Validate frame numbers
    invalid_frames = [f for f in metadata_overrides.keys() if f >= num_frames]
    if invalid_frames:
        raise ValueError(
            f"Frame numbers out of bounds: {invalid_frames} "
            f"(video has {num_frames} frames, 0-indexed)"
        )

    # Merge metadata
    print("Merging metadata...")
    merged_metadata = []

    for frame_num in range(num_frames):
        # Start with original metadata or empty dict
        frame_meta = original_metadata.get(frame_num, {}).copy()

        # Merge overrides if present
        if frame_num in metadata_overrides:
            # If we have a raw packet and overrides, we need to decode, modify, re-encode
            # For now, remove the raw packet so it gets reconstructed with overrides
            if "_raw_klv_packet" in frame_meta:
                del frame_meta["_raw_klv_packet"]

            frame_meta.update(metadata_overrides[frame_num])
            print(
                f"  Frame {frame_num}: Updated {list(metadata_overrides[frame_num].keys())}"
            )

        merged_metadata.append(frame_meta)

    # Get video properties
    cap = cv2.VideoCapture(input_video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    print(f"\nGenerating output video: {width}x{height} @ {fps} fps")
    print(f"Using backend: {backend}")

    # Create frame generator that returns pre-extracted frames
    class PreExtractedFrameGenerator(VideoFrameGenerator):
        def __init__(self, frames_list):
            self.frames_list = frames_list
            # Set dimensions for compatibility
            self.width = frames_list[0].shape[1] if frames_list else 0
            self.height = frames_list[0].shape[0] if frames_list else 0

        def generate_frame(self, frame_num, total_frames, custom_text=None):
            return self.frames_list[frame_num]

    frame_gen = PreExtractedFrameGenerator(frames)

    result = build_klv_video(
        output_path=output_video_path,
        metadata_per_frame=merged_metadata,
        width=width,
        height=height,
        fps=fps,
        frame_generator=frame_gen,
        backend=backend,
    )

    print(f"\nModified video saved to: {result['video_path']}")
    print(f"KLV file saved to: {result['klv_path']}")

    return result
