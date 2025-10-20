"""
GStreamer-based KLV muxing (optional, requires system GStreamer packages).

This module provides an alternative to the FFmpeg-based approach that can
create videos with proper KLVA codec tags matching sample_video.mpg.

Installation requirements:
    sudo apt-get install gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-bad
    pip install "PyGObject<3.51.0"  # For Ubuntu 22.04 with girepository-1.0
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

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
    Experimental GStreamer-based KLV muxer.

    This is an alternative to the FFmpeg approach that aims to create
    proper KLVA codec tags. Currently under development.
    """

    def __init__(self):
        check_gstreamer()
        Gst.init(None)
        self.klv_gen = KLVMetadataGenerator()

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

        NOTE: This is experimental and may not work correctly yet.
        For production use, use the FFmpeg-based video_builder module.

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
        raise NotImplementedError(
            "GStreamer implementation is not yet complete.\n"
            "Use video_builder.build_klv_video() instead."
        )


def build_klv_video_gstreamer(
    output_path: str,
    metadata_per_frame: List[Dict[str, Any]],
    width: int = 64,
    height: int = 64,
    fps: int = 30,
    frame_generator: Optional[VideoFrameGenerator] = None
) -> Dict[str, Any]:
    """
    Build test video with KLV using GStreamer (experimental).

    This function is not yet implemented. Use video_builder.build_klv_video()
    for a working FFmpeg-based solution.

    Args:
        output_path: Output video file path
        metadata_per_frame: List of metadata dictionaries
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Frames per second
        frame_generator: Optional custom frame generator

    Returns:
        Dictionary with generation results

    Raises:
        NotImplementedError: This function is not yet complete
    """
    muxer = GStreamerKLVMuxer()
    return muxer.build_video(
        output_path, metadata_per_frame, width, height, fps, frame_generator
    )
