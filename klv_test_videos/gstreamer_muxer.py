"""
GStreamer-based KLV muxing (optional, requires system GStreamer packages).

This module provides an alternative to the FFmpeg-based approach that can
create videos with proper KLVA codec tags matching sample_video.mpg.

Installation requirements:
    sudo apt-get install gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-bad
    pip install "PyGObject<3.51.0"  # For Ubuntu 22.04 with girepository-1.0
"""

import threading
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib
    GSTREAMER_AVAILABLE = True
except (ImportError, ValueError) as e:
    GSTREAMER_AVAILABLE = False
    GSTREAMER_IMPORT_ERROR = str(e)

from .video_builder import KLVMetadataGenerator, VideoFrameGenerator


def check_gstreamer():
    """Check if GStreamer is available and raise helpful error if not."""
    if not GSTREAMER_AVAILABLE:
        raise ImportError(
            f"GStreamer is not available: {GSTREAMER_IMPORT_ERROR}\n\n"
            "To use GStreamer-based KLV muxing, install:\n"
            "  sudo apt-get install gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-bad\n"
            "  pip install 'PyGObject<3.51.0'"
        )


class GStreamerKLVMuxer:
    """
    GStreamer-based KLV muxer for proper KLVA codec tagging.
    """

    def __init__(self):
        check_gstreamer()
        Gst.init(None)
        self.klv_gen = KLVMetadataGenerator()
        self.loop = None
        self.pipeline = None
        self.error = None

    def build_video(
        self,
        output_path: str,
        metadata_per_frame: List[Dict[str, Any]],
        width: int = 64,
        height: int = 64,
        fps: int = 30,
        frame_generator: Optional[VideoFrameGenerator] = None
    ) -> Dict[str, Any]:
        """
        Build video with KLV using GStreamer.

        Args:
            output_path: Output video file path
            metadata_per_frame: List of metadata dictionaries
            width: Frame width in pixels
            height: Frame height in pixels
            fps: Frames per second
            frame_generator: Optional custom frame generator

        Returns:
            Dictionary with generation results
        """
        num_frames = len(metadata_per_frame)

        if frame_generator is None:
            frame_generator = VideoFrameGenerator(width, height)

        print(f"Generating {num_frames} frames with GStreamer...")

        # Generate frames
        frames = []
        for i in range(num_frames):
            frame = frame_generator.generate_frame(i, num_frames)
            frames.append(frame)

        # Generate KLV packets
        klv_packets = []
        for metadata in metadata_per_frame:
            packet = self.klv_gen.create_packet_from_dict(metadata)
            klv_packets.append(packet)

        total_klv_bytes = sum(len(p) for p in klv_packets)

        # Save KLV to separate file
        klv_output = Path(output_path).with_suffix('.klv')
        with open(klv_output, 'wb') as f:
            for packet in klv_packets:
                f.write(packet)

        # Build and run pipeline
        success = self._run_pipeline(frames, klv_packets, output_path, width, height, fps)

        return {
            "success": success,
            "video_path": output_path,
            "klv_path": str(klv_output),
            "num_frames": num_frames,
            "total_klv_bytes": total_klv_bytes,
            "avg_packet_size": total_klv_bytes / num_frames if num_frames > 0 else 0,
        }

    def _run_pipeline(
        self,
        frames: List[np.ndarray],
        klv_packets: List[bytes],
        output_path: str,
        width: int,
        height: int,
        fps: int
    ) -> bool:
        """Build and run GStreamer pipeline."""

        # Build pipeline string - try different encoders
        # Configure for better seeking: all frames as keyframes
        encoders = [
            ("openh264enc gop-size=1 ! video/x-h264,stream-format=byte-stream ! "
             "h264parse config-interval=-1", None),  # Force all I-frames with gop-size=1
            ("theoraenc", None),  # Theora doesn't need parse
        ]

        pipeline_desc = None
        for encoder, parser in encoders:
            parse_str = f"{parser} ! " if parser else ""
            test_desc = (
                f"appsrc name=videosrc format=time "
                f"caps=video/x-raw,format=BGR,width={width},height={height},framerate={fps}/1 ! "
                f"videoconvert ! "
                f"{encoder} ! "
                f"{parse_str}"
                f"mpegtsmux name=mux ! "
                f"filesink location={output_path} "
                f"appsrc name=klvsrc format=time caps=meta/x-klv,parsed=true ! mux."
            )
            try:
                test_pipeline = Gst.parse_launch(test_desc)
                pipeline_desc = test_desc
                del test_pipeline
                print(f"Using encoder: {encoder}")
                break
            except Exception as e:
                print(f"Encoder {encoder} not available: {e}")
                continue

        if not pipeline_desc:
            print("No suitable encoder found")
            return False

        print(f"Pipeline: {pipeline_desc}")

        try:
            self.pipeline = Gst.parse_launch(pipeline_desc)
        except Exception as e:
            print(f"Failed to create pipeline: {e}")
            return False

        # Get appsrc elements
        video_src = self.pipeline.get_by_name("videosrc")
        klv_src = self.pipeline.get_by_name("klvsrc")

        if not video_src or not klv_src:
            print("Failed to get appsrc elements")
            return False

        # Setup data pushing
        self._setup_data_pushing(video_src, klv_src, frames, klv_packets, fps)

        # Set up bus
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

        # Start pipeline
        print("Starting pipeline...")
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to set pipeline to playing state")
            return False

        # Run main loop in a thread
        self.loop = GLib.MainLoop()
        loop_thread = threading.Thread(target=self.loop.run)
        loop_thread.start()

        # Wait for completion
        loop_thread.join()

        # Cleanup
        self.pipeline.set_state(Gst.State.NULL)

        return self.error is None

    def _setup_data_pushing(self, video_src, klv_src, frames, klv_packets, fps):
        """Set up callbacks to push data to appsrc elements."""

        frame_idx = [0]
        klv_idx = [0]

        def push_video_data(src):
            if frame_idx[0] >= len(frames):
                src.emit("end-of-stream")
                return False

            frame = frames[frame_idx[0]]
            data = frame.tobytes()

            buf = Gst.Buffer.new_wrapped(data)
            buf.pts = frame_idx[0] * Gst.SECOND // fps
            buf.duration = Gst.SECOND // fps

            ret = src.emit("push-buffer", buf)
            if ret != Gst.FlowReturn.OK:
                print(f"Failed to push video buffer: {ret}")
                return False

            frame_idx[0] += 1
            return True

        def push_klv_data(src):
            if klv_idx[0] >= len(klv_packets):
                src.emit("end-of-stream")
                return False

            packet = klv_packets[klv_idx[0]]

            buf = Gst.Buffer.new_wrapped(packet)
            buf.pts = klv_idx[0] * Gst.SECOND // fps
            buf.duration = Gst.SECOND // fps

            ret = src.emit("push-buffer", buf)
            if ret != Gst.FlowReturn.OK:
                print(f"Failed to push KLV buffer: {ret}")
                return False

            klv_idx[0] += 1
            return True

        # Connect need-data signals
        video_src.connect("need-data", lambda src, size: push_video_data(src))
        klv_src.connect("need-data", lambda src, size: push_klv_data(src))

    def _on_message(self, bus, message):
        """Handle bus messages."""
        t = message.type

        if t == Gst.MessageType.EOS:
            print("End of stream")
            if self.loop:
                self.loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")
            self.error = err
            if self.loop:
                self.loop.quit()
        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            print(f"Warning: {warn}, {debug}")
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old, new, pending = message.parse_state_changed()
                print(f"Pipeline state: {old.value_nick} -> {new.value_nick}")


def build_klv_video_gstreamer(
    output_path: str,
    metadata_per_frame: List[Dict[str, Any]],
    width: int = 64,
    height: int = 64,
    fps: int = 30,
    frame_generator: Optional[VideoFrameGenerator] = None
) -> Dict[str, Any]:
    """
    Build test video with KLV using GStreamer.

    This creates videos with proper KLVA codec tags matching sample_video.mpg format.

    Args:
        output_path: Output video file path
        metadata_per_frame: List of metadata dictionaries
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Frames per second
        frame_generator: Optional custom frame generator

    Returns:
        Dictionary with generation results
    """
    muxer = GStreamerKLVMuxer()
    return muxer.build_video(
        output_path, metadata_per_frame, width, height, fps, frame_generator
    )
