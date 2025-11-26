#!/usr/bin/env python3
"""
Example: Modify metadata in sample_video.mpg

This example shows how to take an existing video with KLV metadata
and create a modified version with changed metadata values.
"""

import urllib.request
from pathlib import Path

from vidmeta.video_modifier import modify_video_metadata


def download_sample_video():
    """Download sample video if it doesn't exist."""
    videos_dir = Path("videos")
    videos_dir.mkdir(exist_ok=True)

    video_file = videos_dir / "sample_video.mpg"

    if video_file.exists():
        print(f"✓ Sample video already exists: {video_file}")
        return str(video_file)

    download_url = (
        "https://data.kitware.com/api/v1/file/604a5a532fa25629b931c673/download"
    )

    print("⬇️  Downloading sample video from Kitware...")
    print(f"   URL: {download_url}")
    print(f"   Destination: {video_file}")

    try:
        urllib.request.urlretrieve(download_url, video_file)
        file_size_mb = video_file.stat().st_size / (1024 * 1024)
        print(f"✓ Downloaded successfully ({file_size_mb:.1f} MB)")
        return str(video_file)
    except Exception as e:
        print(f"❌ Failed to download: {e}")
        if video_file.exists():
            video_file.unlink()
        raise


def main():
    print("=" * 60)
    print("Modify Sample Video Example")
    print("=" * 60)
    print()

    # Download sample video if needed
    input_video = download_sample_video()
    output_video = "videos/modified_sample.ts"

    print()
    print("Defining metadata modifications:")
    print()

    # Define metadata changes for specific frames
    metadata_overrides = {
        0: {
            "latitude": 37.7749,  # Change to San Francisco
            "longitude": -122.4194,
        },
        5: {
            "heading": 180.0,  # Change heading to south
            "pitch": -15.0,  # Pitch down (valid range: -20 to +20)
        },
        10: {
            "altitude": 2000.0,  # Lower altitude
            "platform_ground_speed": 50.0,  # Slower speed
        },
        # Add more frame modifications as needed
    }

    for frame_num, changes in metadata_overrides.items():
        print(f"  Frame {frame_num}: {changes}")

    print()
    print("Modifying video...")
    print()

    # Modify the video
    result = modify_video_metadata(
        input_video_path=input_video,
        output_video_path=output_video,
        metadata_overrides=metadata_overrides,
        backend="gstreamer",  # Use GStreamer for proper KLVA tags
    )

    print()
    print("=" * 60)
    print("Modification Complete!")
    print("=" * 60)
    print()
    print(f"Original video:  {input_video}")
    print(f"Modified video:  {result['video_path']}")
    print(f"KLV metadata:    {result['klv_path']}")
    print(f"Frames:          {result['num_frames']}")
    print(f"KLV size:        {result['total_klv_bytes']} bytes")
    print()
    print("You can now load the modified video in burnoutweb or KWIVER")
    print("to see the changed metadata values.")


if __name__ == "__main__":
    main()
