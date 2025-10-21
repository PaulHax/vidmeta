"""Command-line interface for modifying KLV metadata in existing videos."""

import argparse
import json
import sys
from typing import Optional

from .video_modifier import modify_video_metadata


def main(argv: Optional[list] = None):
    """Main CLI entry point for video modification."""
    parser = argparse.ArgumentParser(
        description="Modify KLV metadata in existing videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Modify metadata using JSON file
  modify-klv-video input.mpg -o output.ts --overrides changes.json

  # Modify single field on command line
  modify-klv-video input.mpg -o output.ts --frame 5 --set latitude=37.5

  # Modify multiple fields
  modify-klv-video input.mpg -o output.ts \\
    --frame 0 --set latitude=37.7 longitude=-122.4 \\
    --frame 10 --set altitude=2000

Overrides JSON format:
  {
    "0": {"latitude": 37.7749, "longitude": -122.4194},
    "5": {"heading": 180.0},
    "10": {"altitude": 2000.0, "pitch": -20.0}
  }
        """,
    )

    parser.add_argument("input", help="Input video file with KLV metadata")

    parser.add_argument("-o", "--output", required=True, help="Output video file path")

    parser.add_argument(
        "--overrides",
        type=str,
        help="JSON file with metadata overrides (frame number -> metadata dict)",
    )

    parser.add_argument(
        "--frame",
        type=int,
        action="append",
        dest="frame_numbers",
        help="Frame number to modify (use with --set)",
    )

    parser.add_argument(
        "--set",
        action="append",
        dest="field_sets",
        nargs="+",
        help="Field=value pairs to set for the frame (e.g., latitude=37.5 heading=90)",
    )

    parser.add_argument(
        "--backend",
        type=str,
        choices=["gstreamer", "ffmpeg"],
        default="gstreamer",
        help="Muxing backend: gstreamer (proper KLVA tags, default) or ffmpeg (basic)",
    )

    args = parser.parse_args(argv)

    # Build metadata_overrides from arguments
    metadata_overrides = {}

    # Load from JSON file if provided
    if args.overrides:
        with open(args.overrides, "r") as f:
            json_overrides = json.load(f)
            # Convert string keys to int
            for frame_str, fields in json_overrides.items():
                metadata_overrides[int(frame_str)] = fields

    # Add command-line overrides
    if args.frame_numbers and args.field_sets:
        if len(args.frame_numbers) != len(args.field_sets):
            print(
                "Error: Number of --frame arguments must match number of --set arguments"
            )
            return 1

        for frame_num, field_set in zip(args.frame_numbers, args.field_sets):
            if frame_num not in metadata_overrides:
                metadata_overrides[frame_num] = {}

            # Parse field=value pairs
            for field_value in field_set:
                if "=" not in field_value:
                    print(
                        f"Error: Invalid format '{field_value}', expected field=value"
                    )
                    return 1

                field, value = field_value.split("=", 1)

                # Try to convert to number
                try:
                    if "." in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    # Keep as string
                    pass

                metadata_overrides[frame_num][field] = value

    if not metadata_overrides:
        print("Error: No metadata modifications specified.")
        print("Use --overrides <file.json> or --frame N --set field=value")
        return 1

    print(f"Input video:  {args.input}")
    print(f"Output video: {args.output}")
    print(f"Backend:      {args.backend}")
    print(f"Modifications: {len(metadata_overrides)} frames")
    print()

    try:
        result = modify_video_metadata(
            input_video_path=args.input,
            output_video_path=args.output,
            metadata_overrides=metadata_overrides,
            backend=args.backend,
        )

        print()
        print("✓ Success!")
        print(f"  Video: {result['video_path']}")
        print(f"  KLV:   {result['klv_path']}")
        print(f"  Frames: {result['num_frames']}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
