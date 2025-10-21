"""Modify KLV metadata in existing videos."""

import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple

import cv2
import numpy as np

from .video_builder import build_klv_video, VideoFrameGenerator
from .klv_converter import parse_klv_packet_to_pydantic, pydantic_to_flat_dict


def parse_klv_packet(packet: bytes) -> Tuple[Dict[str, Any], bytes, Dict[str, bytes]]:
    """
    Parse a KLV packet into a metadata dictionary.

    This is a backward-compatible wrapper around the new Pydantic-based parsing.
    For new code, consider using parse_klv_packet_to_pydantic() directly.

    Args:
        packet: Raw KLV packet bytes

    Returns:
        Tuple of (metadata_dict, raw_packet, unknown_tags) where:
        - metadata_dict contains flat keys for backward compatibility
        - raw_packet is the original bytes
        - unknown_tags is a dict of {tag_hex: tag_bytes} for preserving unknown fields
    """
    # Use new Pydantic-based parsing
    parsed = parse_klv_packet_to_pydantic(packet)

    # Convert to flat dict for backward compatibility, extracting unknown tags
    flat_dict, raw_packet, unknown_tags = pydantic_to_flat_dict(parsed)

    return flat_dict, raw_packet, unknown_tags


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


def parse_klv_file(
    klv_path: str,
) -> Dict[int, Tuple[Dict[str, Any], bytes, Dict[str, bytes]]]:
    """
    Parse KLV packets from a file into frame-indexed metadata.

    Args:
        klv_path: Path to file containing raw KLV packets

    Returns:
        Dictionary mapping frame numbers to (metadata_dict, raw_packet, unknown_tags) tuples
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
        metadata_dict, raw_packet, unknown_tags = parse_klv_packet(packet_value)
        metadata_per_frame[frame_num] = (metadata_dict, raw_packet, unknown_tags)
        frame_num += 1

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
        # Get original metadata tuple (metadata_dict, raw_packet, unknown_tags)
        original_tuple = original_metadata.get(frame_num, ({}, None, {}))

        # Unpack tuple - handle both old (2-element) and new (3-element) formats
        if isinstance(original_tuple, tuple):
            if len(original_tuple) == 3:
                frame_meta, raw_packet, unknown_tags = original_tuple
            elif len(original_tuple) == 2:
                # Backward compatibility: old (metadata_dict, raw_packet) format
                frame_meta, raw_packet = original_tuple
                unknown_tags = {}
            else:
                frame_meta = original_tuple
                raw_packet = None
                unknown_tags = {}
        else:
            # Very old format: just a dict
            frame_meta = original_tuple
            raw_packet = None
            unknown_tags = {}

        # Make a copy to avoid modifying original
        frame_meta = frame_meta.copy()

        # Merge overrides if present
        if frame_num in metadata_overrides:
            # When fields are modified, we can't use the raw packet anymore
            # But we CAN preserve unknown tags by storing them separately
            if "_raw_klv_packet" in frame_meta:
                del frame_meta["_raw_klv_packet"]

            # Store unknown tags so video_builder can include them when re-encoding
            if unknown_tags:
                frame_meta["_unknown_klv_tags"] = unknown_tags

            frame_meta.update(metadata_overrides[frame_num])
            print(
                f"  Frame {frame_num}: Updated {list(metadata_overrides[frame_num].keys())}"
            )
            if unknown_tags:
                print(
                    f"  Frame {frame_num}: Preserving {len(unknown_tags)} unknown KLV tags"
                )
        elif raw_packet is not None:
            # No modifications - preserve raw packet for complete pass-through
            frame_meta["_raw_klv_packet"] = raw_packet

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
