#!/usr/bin/env python3
"""
Remove corner points and set frame center lat/lon to marker values in KLV metadata.

This script extracts KLV metadata and:
- Removes corner point fields (tags 26-33)
- Sets Frame Center Latitude (tag 23) to 0.0 (equator - marker value)
- Sets Frame Center Longitude (tag 24) to 0.0 (prime meridian - marker value)
- Keeps Frame Center Elevation (tag 25) with valid value

This creates metadata where frame center lat/lon are present but set to 0.0/0.0
as a marker indicating they should not be used.
"""

import tempfile
from pathlib import Path

import cv2
from klvdata import misb0601

from kwiver_testdata.video_builder import (
    VideoFrameGenerator,
    build_klv_video,
    calculate_klv_checksum,
)
from kwiver_testdata.video_modifier import (
    extract_klv_stream_ffmpeg,
    extract_video_frames,
    parse_klv_file,
)


def remove_fields_from_packet(packet: bytes) -> bytes:
    """
    Remove corner points from a KLV packet.

    Tags to remove:
    - Tag 26-33: Offset Corner Latitude/Longitude Points 1-4

    Note: Frame center lat/lon (tags 23-24) are NOT removed here - they will be
    set to NaN in the metadata dict and re-encoded by build_klv_video.

    Args:
        packet: Raw KLV packet value bytes

    Returns:
        Modified packet with corner points removed
    """
    # Tags to remove - only corner points
    tags_to_remove = set(range(26, 34))  # Corner points (tags 26-33)

    # Rebuild packet without specified tags
    packet_data = bytearray()
    offset = 0

    while offset < len(packet):
        # Read tag
        tag = packet[offset]
        offset += 1

        # Read length (BER encoded)
        length_byte = packet[offset]
        offset += 1

        if length_byte & 0x80:
            # Long form
            num_length_bytes = length_byte & 0x7F
            length = int.from_bytes(packet[offset : offset + num_length_bytes], "big")
            offset += num_length_bytes
        else:
            # Short form
            length = length_byte

        # Read value
        value = packet[offset : offset + length]
        offset += length

        # Skip tags in removal list and checksum (we'll recalculate)
        if tag not in tags_to_remove and tag != 1:  # 1 is checksum
            packet_data.append(tag)
            if length < 128:
                packet_data.append(length)
            else:
                length_bytes = length.to_bytes((length.bit_length() + 7) // 8, "big")
                packet_data.append(0x80 | len(length_bytes))
                packet_data.extend(length_bytes)
            packet_data.extend(value)

    # Add checksum (running sum 16)
    # Per MISB ST 0601.19 section 6.2.2: checksum includes tag+length bytes
    packet_data.append(1)  # Checksum tag
    packet_data.append(2)  # Checksum length

    # Calculate checksum over all data including checksum tag+length
    checksum = calculate_klv_checksum(bytes(packet_data))
    packet_data.extend(checksum.to_bytes(2, byteorder="big"))

    return bytes(packet_data)


def main():
    input_video = "/home/paulhax/src/tele/burnoutweb/test-videos/sample_video.mpg"
    output_video = "videos/sample_video_no_corners_nan_frame_center_latlon.ts"

    print("=" * 60)
    print("Remove Corner Points and Set Frame Center Lat/Lon to Invalid")
    print("=" * 60)
    print(f"\nInput:  {input_video}")
    print(f"Output: {output_video}")
    print()

    # Extract KLV
    print("Extracting KLV stream...")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_klv = Path(temp_dir) / "extracted.klv"
        extract_klv_stream_ffmpeg(input_video, str(temp_klv))

        # Parse KLV metadata
        print("Parsing KLV metadata...")
        original_metadata = parse_klv_file(str(temp_klv))

    # Extract video frames first to know how many we have
    print("Extracting video frames...")
    frames = extract_video_frames(input_video)
    num_video_frames = len(frames)

    # Process each frame's metadata
    print("Removing corner points and setting frame center lat/lon to invalid...")
    modified_metadata = []
    frames_with_corners = 0
    frames_with_frame_center_latlon = 0
    corner_tags = set(range(26, 34))  # Tags 26-33
    frame_center_latlon_tags = {23, 24}  # Tags 23-24 (will be set to 999.0, not removed)

    for frame_num in range(num_video_frames):
        if frame_num in original_metadata:
            # parse_klv_file returns (metadata_dict, raw_packet, unknown_tags)
            metadata_dict, raw_packet, unknown_tags = original_metadata[frame_num]

            # Check if this frame has corner points or frame center lat/lon
            uas_set = misb0601.UASLocalMetadataSet(raw_packet)
            metadata_tags = uas_set.MetadataList()
            has_corners = any(tag in corner_tags for tag in metadata_tags.keys())
            has_frame_center_latlon = any(
                tag in frame_center_latlon_tags for tag in metadata_tags.keys()
            )

            if has_corners:
                frames_with_corners += 1
            if has_frame_center_latlon:
                frames_with_frame_center_latlon += 1

            # Remove specified fields from raw packet
            modified_packet = remove_fields_from_packet(raw_packet)

            # Build new metadata dict
            metadata = metadata_dict.copy()

            # Set frame_center_latitude and frame_center_longitude to marker values
            # Use 0.0, 0.0 (equator/prime meridian intersection) as unlikely real value
            metadata["frame_center_latitude"] = 0.0
            metadata["frame_center_longitude"] = 0.0

            # DO NOT set _raw_klv_packet - this forces build_klv_video to rebuild
            # from dict fields with our marker values
            # metadata["_raw_klv_packet"] = modified_packet

            if unknown_tags:
                metadata["_unknown_klv_tags"] = unknown_tags
            modified_metadata.append(metadata)
        else:
            # No metadata for this frame
            modified_metadata.append({})

    # Get video properties
    cap = cv2.VideoCapture(input_video)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    print(f"\nGenerating output video: {width}x{height} @ {fps} fps")

    # Create frame generator
    class PreExtractedFrameGenerator(VideoFrameGenerator):
        def __init__(self, frames_list):
            self.frames_list = frames_list
            self.width = frames_list[0].shape[1] if frames_list else 0
            self.height = frames_list[0].shape[0] if frames_list else 0

        def generate_frame(self, frame_num, _total_frames, _custom_text=None):
            return self.frames_list[frame_num]

    frame_gen = PreExtractedFrameGenerator(frames)

    # Build video
    result = build_klv_video(
        output_path=output_video,
        metadata_per_frame=modified_metadata,
        width=width,
        height=height,
        fps=fps,
        backend="gstreamer",
        frame_generator=frame_gen,
    )

    print()
    print("=" * 60)
    print("Complete!")
    print("=" * 60)
    print(f"\nGenerated: {result['video_path']}")
    print(f"Total frames: {result['num_frames']}")
    print(f"Metadata frames: {len(original_metadata)}")
    print(f"Frames with corner points: {frames_with_corners}")
    print(f"Frames with frame center lat/lon: {frames_with_frame_center_latlon}")
    print(f"KLV bytes: {result['total_klv_bytes']}")
    print()
    if frames_with_corners > 0 or frames_with_frame_center_latlon > 0:
        print(
            f"✓ Removed corner points from {frames_with_corners} frames "
            f"and set frame center lat/lon to 0.0/0.0 (marker values) in {frames_with_frame_center_latlon} frames."
        )
        print("  Frame center elevation (altitude) preserved with valid values.")
    else:
        print("ℹ No matching fields found in video.")


if __name__ == "__main__":
    main()
