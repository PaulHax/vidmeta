# KLV Test Videos

Generate test videos with KLV metadata streams for testing burnoutweb and KWIVER.

## Installation

### Basic Installation (FFmpeg-based)

```bash
cd klv-test-videos
uv pip install -e .
```

### GStreamer Support (Recommended for KWIVER Testing)

For GStreamer-based KLV muxing with proper KLVA codec tags, correct checksums, and full seeking support:

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install libgirepository1.0-dev gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-bad gstreamer1.0-plugins-good gstreamer1.0-openh264

# Install with GStreamer support
uv pip install -e ".[gstreamer]"
```

**Why use GStreamer?**
- Proper KLVA codec tags (vs generic bin_data from FFmpeg)
- Correct running sum 16 checksums compatible with KWIVER
- All I-frames for full seeking support (forward and backward)
- Better compatibility with KWIVER's video readers

## CLI Usage

```bash
# Generate video matching sample_video.mpg frame 812
generate-klv-video sample_video

# List available scenarios
generate-klv-video --list

# Generate all scenarios
generate-klv-video --all

# Custom output and size
generate-klv-video moving --output my_test.mpg --width 128 --height 128
```

Available scenarios: `sample_video`, `stationary`, `moving`, `high_altitude`, `minimal`

Each generates:
- `.mpg` file - MPEG-TS video with embedded KLV data stream
- `.klv` file - Raw KLV packets (use this for KWIVER testing)

**Note**: The KLV data is embedded in the MPEG-TS stream, but FFmpeg cannot replicate the full KLVA codec tagging found in professional tools. For reliable KWIVER testing, use the separate `.klv` file which contains properly formatted MISB ST 0601 packets.

## Python API

### GStreamer API (Recommended)

Self-contained example for generating KLV test videos with proper KLVA codec tags (see `examples/example_gstreamer.py` for complete runnable example):

```python
from datetime import datetime, timezone
from klv_test_videos.gstreamer_muxer import build_klv_video_gstreamer

# Define metadata for each frame
metadata = [
    {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'altitude': 500.0,
        'heading': 45.0,
        'pitch': -15.0,
        'roll': 0.0,
        'horizontal_fov': 60.0,
        'vertical_fov': 45.0,
        'slant_range': 5000.0,
        'mission_id': 'TEST_001',
        'platform_designation': 'Test Platform',
        'sensor_name': 'EO Sensor',
        'timestamp': datetime.now(timezone.utc),
    },
    # ... one dict per frame (add more frames as needed)
]

# Generate video with GStreamer
result = build_klv_video_gstreamer(
    output_path='test.ts',
    metadata_per_frame=metadata,
    width=256,
    height=256,
    fps=30
)

print(f"Video: {result['video_path']}")
print(f"KLV file: {result['klv_path']}")
print(f"Frames: {result['num_frames']}")
```

### FFmpeg API (Basic)

```python
from datetime import datetime, timezone
from klv_test_videos.video_builder import build_klv_video

metadata = [
    {
        'latitude': 37.7749,
        'longitude': -122.4194,
        'altitude': 500.0,
        'heading': 45.0,
        'pitch': -15.0,
        'roll': 0.0,
        'horizontal_fov': 60.0,
        'vertical_fov': 45.0,
        'slant_range': 5000.0,
        'mission_id': 'TEST_001',
        'timestamp': datetime.now(timezone.utc),
    },
    # ... one dict per frame
]

result = build_klv_video(
    output_path='test.mpg',
    metadata_per_frame=metadata,
    width=64,
    height=64,
    fps=30
)
```

## Supported Metadata Fields

All optional (except `version`):

**Position**: `latitude`, `longitude`, `altitude`
**Orientation**: `heading`, `pitch`, `roll`
**Sensor**: `sensor_relative_azimuth`, `sensor_relative_elevation`, `sensor_relative_roll`
**FOV**: `horizontal_fov`, `vertical_fov`
**Range**: `slant_range`, `ground_range`, `target_width`
**Identification**: `mission_id`, `platform_call_sign`, `platform_designation`, `platform_tail_number`, `sensor_name`
**Other**: `platform_ground_speed`, `timestamp`, `version`
