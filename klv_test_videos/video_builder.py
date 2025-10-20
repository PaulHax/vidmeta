"""Core functions for building test videos with KLV metadata."""

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from klvdata import common, misb0601


class KLVMetadataGenerator:
    """Generates MISB ST 0601 KLV metadata packets from metadata dictionaries."""

    # UAS Local Set Universal Key (16 bytes)
    UAS_LS_KEY = bytes(
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

    def create_packet_from_dict(self, metadata: Dict[str, Any]) -> bytes:
        """
        Create a KLV packet from a metadata dictionary.

        If metadata contains '_raw_klv_packet', use it directly for pass-through.

        Args:
            metadata: Dictionary with metadata keys and values. Supported keys:
                - version: UAS LS version (default: 1)
                - timestamp: datetime object or unix timestamp in microseconds
                - mission_id: Mission identifier string
                - latitude: Sensor latitude in degrees
                - longitude: Sensor longitude in degrees
                - altitude: Sensor altitude in meters
                - heading: Platform heading in degrees (0-360)
                - pitch: Platform pitch in degrees
                - roll: Platform roll in degrees
                - horizontal_fov: Horizontal field of view in degrees
                - vertical_fov: Vertical field of view in degrees
                - slant_range: Slant range in meters
                - platform_call_sign: Platform call sign
                - platform_designation: Platform designation string
                - sensor_name: Sensor name/designation

        Returns:
            Complete KLV packet as bytes
        """
        # If raw packet exists, use it for pass-through (no modifications)
        if "_raw_klv_packet" in metadata:
            value_bytes = metadata["_raw_klv_packet"]
            length_bytes = common.ber_encode(len(value_bytes))
            return self.UAS_LS_KEY + length_bytes + value_bytes

        elements = []

        # 1. UAS LS Version Number (mandatory)
        version = metadata.get("version", 1)
        elements.append(misb0601.UASLSVersionNumber(version))

        # 2. Precision Time Stamp
        if "timestamp" in metadata:
            timestamp = metadata["timestamp"]
            if isinstance(timestamp, (int, float)):
                # Convert microseconds to datetime
                timestamp = datetime.fromtimestamp(
                    timestamp / 1_000_000, tz=timezone.utc
                )

            # Manually encode (klvdata constructors are for parsing)
            timestamp_bytes = common.datetime_to_bytes(timestamp)
            ts_key = b"\x02"
            ts_length = common.ber_encode(len(timestamp_bytes))
            elements.append(ts_key + ts_length + timestamp_bytes)

        # 3. Mission ID
        if "mission_id" in metadata:
            elements.append(misb0601.MissionID(metadata["mission_id"]))

        # 4. Platform Designation
        if "platform_designation" in metadata:
            elements.append(
                misb0601.PlatformDesignation(metadata["platform_designation"])
            )

        # 5. Platform Call Sign
        if "platform_call_sign" in metadata:
            elements.append(misb0601.PlatformCallSign(metadata["platform_call_sign"]))

        # 6. Platform Tail Number
        if "platform_tail_number" in metadata:
            elements.append(
                misb0601.PlatformTailNumber(metadata["platform_tail_number"])
            )

        # 7. Sensor Name
        if "sensor_name" in metadata:
            elements.append(misb0601.ImageSourceSensor(metadata["sensor_name"]))

        # 8. Sensor Position
        if "latitude" in metadata:
            elements.append(misb0601.SensorLatitude(metadata["latitude"]))

        if "longitude" in metadata:
            elements.append(misb0601.SensorLongitude(metadata["longitude"]))

        if "altitude" in metadata:
            elements.append(misb0601.SensorTrueAltitude(metadata["altitude"]))

        # 9. Platform Orientation
        if "heading" in metadata:
            elements.append(misb0601.PlatformHeadingAngle(metadata["heading"]))

        if "pitch" in metadata:
            elements.append(misb0601.PlatformPitchAngle(metadata["pitch"]))

        if "roll" in metadata:
            elements.append(misb0601.PlatformRollAngle(metadata["roll"]))

        # 10. Sensor Angles (relative to platform)
        if "sensor_relative_azimuth" in metadata:
            elements.append(
                misb0601.SensorRelativeAzimuthAngle(metadata["sensor_relative_azimuth"])
            )

        if "sensor_relative_elevation" in metadata:
            elements.append(
                misb0601.SensorRelativeElevationAngle(
                    metadata["sensor_relative_elevation"]
                )
            )

        if "sensor_relative_roll" in metadata:
            elements.append(
                misb0601.SensorRelativeRollAngle(metadata["sensor_relative_roll"])
            )

        # 11. Field of View
        if "horizontal_fov" in metadata:
            elements.append(
                misb0601.SensorHorizontalFieldOfView(metadata["horizontal_fov"])
            )

        if "vertical_fov" in metadata:
            elements.append(
                misb0601.SensorVerticalFieldOfView(metadata["vertical_fov"])
            )

        # 12. Slant Range
        if "slant_range" in metadata:
            elements.append(misb0601.SlantRange(metadata["slant_range"]))

        # 13. Additional fields
        if "target_width" in metadata:
            elements.append(misb0601.TargetWidth(metadata["target_width"]))

        if "ground_range" in metadata:
            elements.append(misb0601.GroundRange(metadata["ground_range"]))

        if "platform_ground_speed" in metadata:
            elements.append(
                misb0601.PlatformGroundSpeed(metadata["platform_ground_speed"])
            )

        # 14. Frame Center
        if "frame_center_latitude" in metadata:
            elements.append(
                misb0601.FrameCenterLatitude(metadata["frame_center_latitude"])
            )

        if "frame_center_longitude" in metadata:
            elements.append(
                misb0601.FrameCenterLongitude(metadata["frame_center_longitude"])
            )

        if "frame_center_elevation" in metadata:
            elements.append(
                misb0601.FrameCenterElevation(metadata["frame_center_elevation"])
            )

        # Combine all elements
        value_bytes = b""
        for elem in elements:
            if isinstance(elem, bytes):
                value_bytes += elem
            else:
                value_bytes += bytes(elem)

        # Add checksum (MISB ST0601 tag 1)
        # Calculate CRC-16-CCITT over value_bytes
        checksum = self._calculate_checksum(value_bytes)
        checksum_key = b"\x01"
        checksum_value = checksum.to_bytes(2, byteorder="big")
        checksum_length = common.ber_encode(len(checksum_value))
        value_bytes += checksum_key + checksum_length + checksum_value

        # Create complete packet: Key + Length + Value
        length_bytes = common.ber_encode(len(value_bytes))
        packet = self.UAS_LS_KEY + length_bytes + value_bytes

        return packet

    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate running sum 16 checksum for MISB ST0601."""
        checksum = 0
        for i, byte in enumerate(data):
            if i % 2 == 0:
                checksum += byte << 8
            else:
                checksum += byte
            checksum &= 0xFFFF
        return checksum


class VideoFrameGenerator:
    """Generates video frames with visual markers."""

    def __init__(self, width: int = 64, height: int = 64):
        """
        Initialize frame generator.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels
        """
        self.width = width
        self.height = height

    def generate_frame(
        self, frame_num: int, total_frames: int, custom_text: Optional[str] = None
    ) -> np.ndarray:
        """
        Generate a single frame with visual markers.

        Args:
            frame_num: Current frame number (0-indexed)
            total_frames: Total number of frames
            custom_text: Optional custom text to display instead of frame number

        Returns:
            Frame as numpy array (BGR format)
        """
        # Create frame with changing background color
        hue = int((frame_num / max(total_frames, 1)) * 179)  # HSV hue: 0-179
        frame_hsv = np.full(
            (self.height, self.width, 3), [hue, 200, 200], dtype=np.uint8
        )
        frame = cv2.cvtColor(frame_hsv, cv2.COLOR_HSV2BGR)

        # Add frame number or custom text
        text = custom_text if custom_text else f"{frame_num}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = min(0.5, self.width / 128)  # Scale font with frame size
        thickness = max(1, int(self.width / 64))
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]

        # Center the text
        text_x = (self.width - text_size[0]) // 2
        text_y = (self.height + text_size[1]) // 2

        cv2.putText(
            frame,
            text,
            (text_x, text_y),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )

        # Add corner markers
        marker_size = max(2, self.width // 20)
        cv2.circle(frame, (5, 5), marker_size, (0, 255, 0), -1)  # Top-left
        cv2.circle(
            frame, (self.width - 5, 5), marker_size, (0, 0, 255), -1
        )  # Top-right
        cv2.circle(
            frame, (5, self.height - 5), marker_size, (255, 0, 0), -1
        )  # Bottom-left
        cv2.circle(
            frame, (self.width - 5, self.height - 5), marker_size, (255, 255, 0), -1
        )  # Bottom-right

        return frame


def build_klv_video(
    output_path: str,
    metadata_per_frame: List[Dict[str, Any]],
    width: int = 64,
    height: int = 64,
    fps: int = 30,
    frame_generator: Optional[VideoFrameGenerator] = None,
    backend: str = "gstreamer",
) -> Dict[str, Any]:
    """
    Build a test video with KLV metadata from a list of metadata dictionaries.

    Unified API with backend selection.

    Args:
        output_path: Output video file path (.ts for MPEG-TS format)
        metadata_per_frame: List of metadata dictionaries, one per frame
        width: Frame width in pixels (default: 64)
        height: Frame height in pixels (default: 64)
        fps: Frames per second (default: 30)
        frame_generator: Optional custom frame generator
        backend: Muxing backend - "gstreamer" (default) or "ffmpeg"

    Returns:
        Dictionary with generation results:
            - success: bool
            - video_path: str
            - klv_path: str (separate KLV file)
            - num_frames: int
            - total_klv_bytes: int

    Example:
        >>> metadata = [
        ...     {"latitude": 37.77, "longitude": -122.42, "altitude": 500, "heading": 45},
        ...     {"latitude": 37.78, "longitude": -122.41, "altitude": 510, "heading": 50},
        ... ]
        >>> result = build_klv_video("test.ts", metadata, backend="gstreamer")
    """
    if backend == "gstreamer":
        try:
            from .gstreamer_muxer import build_klv_video_gstreamer

            return build_klv_video_gstreamer(
                output_path, metadata_per_frame, width, height, fps, frame_generator
            )
        except ImportError as e:
            print(f"GStreamer backend not available: {e}")
            print("Falling back to FFmpeg backend...")
            backend = "ffmpeg"

    if backend != "ffmpeg":
        raise ValueError(f"Unknown backend: {backend}. Use 'gstreamer' or 'ffmpeg'")

    # FFmpeg backend implementation
    num_frames = len(metadata_per_frame)

    if frame_generator is None:
        frame_generator = VideoFrameGenerator(width, height)

    klv_gen = KLVMetadataGenerator()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        video_file = temp_path / "video.mp4"
        klv_file = temp_path / "metadata.klv"

        # Generate video frames
        print(f"Generating {num_frames} frames at {width}x{height}...")

        # Use MJPEG codec for better compatibility
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        video_writer = cv2.VideoWriter(str(video_file), fourcc, fps, (width, height))

        for i in range(num_frames):
            frame = frame_generator.generate_frame(i, num_frames)
            video_writer.write(frame)

        video_writer.release()

        # Generate KLV metadata
        print(f"Generating KLV metadata for {num_frames} frames...")

        with open(klv_file, "wb") as f:
            for i, metadata in enumerate(metadata_per_frame):
                packet = klv_gen.create_packet_from_dict(metadata)
                f.write(packet)

        total_klv_bytes = klv_file.stat().st_size

        # Save KLV separately
        klv_output = Path(output_path).with_suffix(".klv")
        import shutil

        shutil.copy(klv_file, klv_output)

        # Mux with FFmpeg
        print("Muxing video and KLV with FFmpeg...")

        # Try to create proper KLV-embedded MPEG-TS
        # Note: FFmpeg has limited support for muxing raw KLV into MPEG-TS
        # The stream will be marked as 'data' rather than 'klv (KLVA)'
        # For full KLVA support, professional tools are typically needed

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-r",
            str(fps),  # Input frame rate
            "-i",
            str(video_file),
            "-f",
            "data",
            "-i",
            str(klv_file),
            "-map",
            "0:v",
            "-map",
            "1:0",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",  # Ensure compatible pixel format
            "-r",
            str(fps),  # Output frame rate
            "-g",
            str(fps),  # Keyframe interval (every second)
            "-x264-params",
            "bframes=0:keyint={}:scenecut=0".format(fps),  # No B-frames
            "-bsf:v",
            "h264_mp4toannexb",  # Convert to Annex-B for MPEG-TS
            "-muxdelay",
            "0",  # No muxing delay
            "-muxpreload",
            "0",  # No muxing preload
            "-c:d",
            "copy",  # Copy data stream
            "-metadata:s:d:0",
            "language=klv",  # Try to hint KLV
            "-f",
            "mpegts",  # MPEG-TS format (same as sample_video.mpg)
            output_path,
        ]

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        # Note in output that KLV is embedded but not with full KLVA tagging
        if result.returncode == 0:
            print("\nNote: KLV data is embedded in MPEG-TS stream.")
            print("      For KWIVER testing, use the separate .klv file.")
            print("      (FFmpeg cannot fully replicate KLVA codec tagging)")

        success = result.returncode == 0
        if not success:
            print("Warning: FFmpeg muxing may have issues.")
            print(f"KLV saved separately to: {klv_output}")

        return {
            "success": success,
            "video_path": output_path,
            "klv_path": str(klv_output),
            "num_frames": num_frames,
            "total_klv_bytes": total_klv_bytes,
            "avg_packet_size": total_klv_bytes / num_frames if num_frames > 0 else 0,
        }
