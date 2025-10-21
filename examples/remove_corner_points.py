#!/usr/bin/env python3
"""
Remove corner points from KLV metadata in a video.

This script extracts KLV metadata, removes corner point fields (tags 26-33),
and regenerates the video with the modified metadata.
"""

import tempfile
from pathlib import Path

from klvdata import misb0601


def remove_corner_points_from_packet(packet: bytes) -> bytes:
    """
    Remove corner point fields from a KLV packet.

    Corner point tags to remove:
    - Tag 26-29: Offset Corner Latitude/Longitude Point 1-2
    - Tag 30-33: Offset Corner Latitude/Longitude Point 3-4

    Args:
        packet: Raw KLV packet value bytes

    Returns:
        Modified packet with corner points removed
    """
    # Tags to remove (corner points)
    corner_tags = set(range(26, 34))  # Tags 26-33

    # Rebuild packet without corner point tags
    # We'll extract raw tag bytes and skip corner point tags
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

        # Skip corner point tags and checksum (we'll recalculate)
        if tag not in corner_tags and tag != 1:  # 1 is checksum
            packet_data.append(tag)
            if length < 128:
                packet_data.append(length)
            else:
                length_bytes = length.to_bytes((length.bit_length() + 7) // 8, "big")
                packet_data.append(0x80 | len(length_bytes))
                packet_data.extend(length_bytes)
            packet_data.extend(value)

    # Add checksum (running sum 16 - same as video_builder)
    checksum = 0
    for i, byte in enumerate(packet_data):
        if i % 2 == 0:
            checksum += byte << 8
        else:
            checksum += byte
        checksum &= 0xFFFF

    packet_data.append(1)  # Checksum tag
    packet_data.append(2)  # Checksum length
    packet_data.extend(checksum.to_bytes(2, byteorder="big"))

    return bytes(packet_data)


def main():
    input_video = "/home/paulhax/src/tele/burnoutweb/test-videos/sample_video.mpg"
    output_video = (
        "/home/paulhax/src/tele/klv-test-videos/videos/sample_video_no_corners.ts"
    )

    print("=" * 60)
    print("Remove Corner Points from Video")
    print("=" * 60)
    print(f"\nInput:  {input_video}")
    print(f"Output: {output_video}")
    print()

    # Use the video modifier with a custom pass-through
    from klv_test_videos.video_modifier import (
        extract_klv_stream_ffmpeg,
        parse_klv_file,
        extract_video_frames,
    )
    from klv_test_videos.video_builder import build_klv_video, VideoFrameGenerator
    import cv2

    # Extract KLV
    print("Extracting KLV stream...")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_klv = Path(temp_dir) / "extracted.klv"
        extract_klv_stream_ffmpeg(input_video, str(temp_klv))

        # Parse KLV and check for corner points
        print("Parsing KLV metadata...")
        original_metadata = parse_klv_file(str(temp_klv))

        # Debug: Check if corner points exist in the original
        print("\nChecking for corner points in original video...")
        frames_with_corners = 0
        sample_frame = None
        for frame_num, metadata in list(original_metadata.items())[:10]:
            if "_raw_klv_packet" in metadata:
                packet = metadata["_raw_klv_packet"]
                # Parse to check for corner tags (26-33)
                uas_set = misb0601.UASLocalMetadataSet(packet)
                metadata_dict = uas_set.MetadataList()
                corner_tags = set(range(26, 34))
                found_corners = [
                    tag for tag in metadata_dict.keys() if tag in corner_tags
                ]
                if found_corners:
                    frames_with_corners += 1
                    if sample_frame is None:
                        sample_frame = frame_num
                        print(
                            f"  Frame {frame_num} has corner point tags: {found_corners}"
                        )

        print("  Total frames checked: 10")
        print(f"  Frames with corner points: {frames_with_corners}")

        if frames_with_corners == 0:
            print("\n⚠️  WARNING: No corner points found in input video!")
            print("   The input video may not have corner point metadata.")
            return

        print("\n✓ Corner points found. Proceeding with removal...")
        print("Removing corner points from metadata...")

    # Extract video frames first to know how many we have
    print("Extracting video frames...")
    frames = extract_video_frames(input_video)
    num_video_frames = len(frames)

    # Process each frame's metadata to remove corner points (only for frames we have)
    modified_metadata = []
    for frame_num in range(num_video_frames):
        if frame_num in original_metadata:
            metadata = original_metadata[frame_num].copy()
            if "_raw_klv_packet" in metadata:
                # Remove corner points from raw packet
                raw_packet = metadata["_raw_klv_packet"]
                modified_packet = remove_corner_points_from_packet(raw_packet)
                metadata["_raw_klv_packet"] = modified_packet
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
    print(f"Frames: {result['num_frames']}")
    print(f"KLV bytes: {result['total_klv_bytes']}")
    print()
    print("Corner points have been removed from all frames.")


if __name__ == "__main__":
    main()
