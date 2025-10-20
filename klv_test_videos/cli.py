"""Command-line interface for generating KLV test videos."""

import argparse
import sys
from typing import Optional

from .video_builder import build_klv_video
from .scenarios import SCENARIOS, get_scenario, list_scenarios


def main(argv: Optional[list] = None):
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate test videos with KLV metadata streams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate video matching sample_video.mpg
  generate-klv-video sample_video

  # Generate a moving camera scenario
  generate-klv-video moving --output my_test.ts

  # Generate all scenarios
  generate-klv-video --all

  # List available scenarios
  generate-klv-video --list
        """
    )

    parser.add_argument(
        'scenario',
        nargs='?',
        help='Scenario name (use --list to see available scenarios)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output video file path (default: scenario-specific name)',
        type=str
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available scenarios and exit'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Generate all available scenarios'
    )

    parser.add_argument(
        '--width',
        type=int,
        default=64,
        help='Frame width in pixels (default: 64)'
    )

    parser.add_argument(
        '--height',
        type=int,
        default=64,
        help='Frame height in pixels (default: 64)'
    )

    parser.add_argument(
        '--fps',
        type=int,
        default=30,
        help='Frames per second (default: 30)'
    )

    parser.add_argument(
        '--backend',
        type=str,
        choices=['gstreamer', 'ffmpeg'],
        default='gstreamer',
        help='Muxing backend: gstreamer (proper KLVA tags, default) or ffmpeg (basic)'
    )

    args = parser.parse_args(argv)

    # List scenarios
    if args.list:
        print("Available scenarios:")
        print()
        for name, info in SCENARIOS.items():
            print(f"  {name}")
            print(f"    {info['description']}")
            print(f"    Default output: {info['default_output']}")
            print()
        return 0

    # Generate all scenarios
    if args.all:
        print(f"Generating {len(SCENARIOS)} test scenarios...")
        print()

        for i, (name, info) in enumerate(SCENARIOS.items(), 1):
            print(f"[{i}/{len(SCENARIOS)}] {info['name']}")
            print(f"  {info['description']}")

            metadata = info['generator']()
            output = args.output if args.output else info['default_output']

            result = build_klv_video(
                output_path=output,
                metadata_per_frame=metadata,
                width=args.width,
                height=args.height,
                fps=args.fps,
                backend=args.backend
            )

            print(f"  ✓ Generated: {result['video_path']}")
            print(f"  ✓ KLV file: {result['klv_path']}")
            print(f"  ✓ Frames: {result['num_frames']}, "
                  f"KLV size: {result['total_klv_bytes']} bytes, "
                  f"avg: {result['avg_packet_size']:.1f} bytes/frame")
            print()

        print(f"All {len(SCENARIOS)} scenarios generated successfully!")
        return 0

    # Generate single scenario
    if not args.scenario:
        parser.print_help()
        print("\nError: scenario name required (use --list to see available scenarios)")
        return 1

    try:
        scenario = get_scenario(args.scenario)
    except ValueError as e:
        print(f"Error: {e}")
        print(f"\nUse --list to see available scenarios")
        return 1

    print(f"Generating scenario: {scenario['name']}")
    print(f"  {scenario['description']}")
    print()

    metadata = scenario['generator']()
    output = args.output if args.output else scenario['default_output']

    result = build_klv_video(
        output_path=output,
        metadata_per_frame=metadata,
        width=args.width,
        height=args.height,
        fps=args.fps,
        backend=args.backend
    )

    if result['success']:
        print(f"\n✓ Success!")
    else:
        print(f"\n⚠ Video generated with warnings")

    print(f"  Video: {result['video_path']}")
    print(f"  KLV:   {result['klv_path']}")
    print(f"  Frames: {result['num_frames']}")
    print(f"  KLV size: {result['total_klv_bytes']} bytes")
    print(f"  Avg packet: {result['avg_packet_size']:.1f} bytes/frame")

    return 0


if __name__ == '__main__':
    sys.exit(main())
