#!/usr/bin/env python3
"""
Self-contained example for generating KLV test videos.

This example shows how to create a video with KLV metadata from a dictionary
of key-value pairs. The generated video will have:
- Proper KLVA codec tags for KWIVER compatibility
- Correct running sum 16 checksums
- All I-frames for full seeking support
"""

from datetime import datetime, timezone

from klv_test_videos.video_builder import build_klv_video


def main():
    # Define metadata for each frame
    # Each dictionary represents one frame's metadata
    metadata_per_frame = [
        {
            # Required
            "version": 7,  # UAS LS Version
            # Position
            "latitude": 37.7749,  # degrees
            "longitude": -122.4194,  # degrees
            "altitude": 500.0,  # meters above MSL
            # Platform orientation
            "heading": 45.0,  # degrees (0-360)
            "pitch": -15.0,  # degrees
            "roll": 0.0,  # degrees
            # Sensor angles (relative to platform)
            "sensor_relative_azimuth": 0.0,  # degrees
            "sensor_relative_elevation": -45.0,  # degrees
            "sensor_relative_roll": 0.0,  # degrees
            # Field of view
            "horizontal_fov": 60.0,  # degrees
            "vertical_fov": 45.0,  # degrees
            # Range
            "slant_range": 5000.0,  # meters
            "ground_range": 4000.0,  # meters
            "target_width": 100.0,  # meters
            # Identification
            "mission_id": "TEST_MISSION_001",
            "platform_designation": "Test UAV Platform",
            "platform_call_sign": "TESTBIRD1",
            "platform_tail_number": "N12345",
            "sensor_name": "EO/IR Sensor",
            # Other
            "platform_ground_speed": 25.0,  # m/s
            "timestamp": datetime.now(timezone.utc),
        },
        # Add more frames as needed
        # You can vary any of the values between frames to simulate motion
    ]

    # For this example, create 10 frames with gradually changing position
    for i in range(1, 10):
        frame_metadata = metadata_per_frame[0].copy()
        # Simulate movement: increment latitude and heading
        frame_metadata["latitude"] += i * 0.0001
        frame_metadata["longitude"] += i * 0.0001
        frame_metadata["heading"] = (45.0 + i * 5) % 360
        frame_metadata["timestamp"] = datetime.fromtimestamp(
            metadata_per_frame[0]["timestamp"].timestamp() + i / 30.0, tz=timezone.utc
        )
        metadata_per_frame.append(frame_metadata)

    print(f"Generating video with {len(metadata_per_frame)} frames...")
    print()

    # Generate video (uses GStreamer backend by default)
    result = build_klv_video(
        output_path="videos/example_output.ts",
        metadata_per_frame=metadata_per_frame,
        width=256,  # Frame width in pixels
        height=256,  # Frame height in pixels
        fps=30,  # Frames per second
        backend="gstreamer",  # Or 'ffmpeg' for basic muxing
    )

    # Print results
    print()
    if result["success"]:
        print("✓ Video generated successfully!")
    else:
        print("⚠ Video generation completed with warnings")

    print()
    print(f"Video file:    {result['video_path']}")
    print(f"KLV file:      {result['klv_path']}")
    print(f"Frames:        {result['num_frames']}")
    print(f"Total KLV:     {result['total_klv_bytes']} bytes")
    print(f"Avg per frame: {result['avg_packet_size']:.1f} bytes")
    print()
    print("You can now load the video in burnoutweb or KWIVER for testing.")


if __name__ == "__main__":
    main()
