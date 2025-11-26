# vidmeta

Parse, analyze, and generate test videos with embedded geospatial and sensor metadata (MISB ST 0601 KLV). Primarily used for testing KWIVER and related computer vision tools.

## Installation

### Metadata Analysis Only

For parsing and analyzing KLV metadata (no video generation):

```bash
pip install vidmeta
```

### With Video Muxing

To generate or modify videos with embedded KLV metadata:

```bash
pip install vidmeta[mux]
```

This adds OpenCV and PyGObject dependencies. You'll also need GStreamer system packages.

#### Ubuntu/Debian

```bash
# Core GStreamer packages
sudo apt-get update
sudo apt-get install -y \
    libgirepository1.0-dev \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad

# OpenH264 codec (recommended for best compatibility)
sudo apt-get install -y gstreamer1.0-openh264

# Install vidmeta with video support
pip install vidmeta[mux]
```

#### Fedora/RHEL/CentOS

```bash
# Enable RPM Fusion for additional codecs
sudo dnf install -y \
    https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm

# Core packages
sudo dnf install -y \
    gobject-introspection-devel \
    gstreamer1-devel \
    gstreamer1-plugins-base-devel \
    gstreamer1-plugins-good \
    gstreamer1-plugins-bad-free \
    gstreamer1-plugin-openh264

pip install vidmeta[mux]
```

#### macOS (Homebrew)

```bash
brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad
pip install vidmeta[mux]
```

#### Docker (All Platforms)

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgirepository1.0-dev \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-openh264 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install vidmeta[mux]
```

#### Verify Video Installation

```bash
# Check GStreamer version (1.16+ recommended)
gst-inspect-1.0 --version

# Verify mpegtsmux element (required for KLV muxing)
gst-inspect-1.0 mpegtsmux

# Verify openh264 encoder (optional but recommended)
gst-inspect-1.0 openh264enc
```

#### Troubleshooting Video Generation

**"GStreamer is not available" error:**
- Ensure `gir1.2-gstreamer-1.0` package is installed (provides Python bindings)
- Check PyGObject version: `pip show PyGObject` (should be >= 3.44.0)

**"No suitable encoder found" error:**
- Install `gstreamer1.0-openh264` for H.264 encoding
- Fallback uses Theora if H.264 unavailable

**PyGObject version conflicts:**
```bash
# For Ubuntu 22.04 with girepository-1.0
pip install 'PyGObject>=3.44.0,<3.51.0'
```

#### Why GStreamer (Not FFmpeg)?

FFmpeg CLI cannot set KLVA codec tags for data streams - it creates generic "bin_data" streams. GStreamer's `mpegtsmux` provides:

- **KLVA codec tags** - Required by KWIVER to recognize metadata streams
- **MISB ST 0601 checksums** - Running sum 16 validation
- **All I-frames** - Full forward/backward seeking support
- **Synchronous KLV** - Optional MISB ST 1402 compliance (stream_type=21)

## CLI Usage

```bash
# Generate video matching sample_video.mpg frame 812
vidmeta-generate sample_video

# List available scenarios
vidmeta-generate --list

# Generate all scenarios
vidmeta-generate --all

# Custom output and size
vidmeta-generate moving --output videos/my_test.ts --width 256 --height 256
```

## Running Example Scripts

```bash
# Remove corner points from video (keeps frame center lat/lon)
uv run python examples/remove_corner_points.py

# Remove corner points AND make frame center lat/lon unparseable
# (writes 0-byte length for tags 23-24)
uv run python examples/remove_corners_and_frame_center_latlon.py
```

Available scenarios: `sample_video`, `stationary`, `moving`, `high_altitude`, `minimal`

Each generates:

- `.ts` or `.mpg` file - MPEG-TS video with embedded KLV data stream (both extensions work)
- `.klv` file - Raw KLV packets for KWIVER testing (MISB ST 0601 format)

## Python API

### Parsing KLV Metadata

Parse KLV packets into typed Pydantic models (no video dependencies required):

```python
from vidmeta.klv_converter import parse_klv_packet_to_pydantic

# Parse a raw KLV packet
with open('metadata.klv', 'rb') as f:
    raw_packet = f.read()

parsed = parse_klv_packet_to_pydantic(raw_packet)

# Access structured metadata
print(f"Latitude: {parsed.metadata.platform.latitude}")
print(f"Altitude: {parsed.metadata.platform.altitude}")
print(f"Heading: {parsed.metadata.platform.heading}")
print(f"Timestamp: {parsed.metadata.timestamp}")
```

### Generating Videos

Unified API with backend selection (see `examples/example_gstreamer.py` for complete runnable example):

```python
from datetime import datetime, timezone
from vidmeta.video_builder import build_klv_video

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

# Generate video with GStreamer backend (default, recommended)
result = build_klv_video(
    output_path='videos/test.ts',
    metadata_per_frame=metadata,
    width=256,
    height=256,
    fps=30,
    backend='gstreamer'  # Default; provides proper KLVA tags, checksums, and seeking
)

# Or use FFmpeg backend for basic muxing
result = build_klv_video(
    output_path='videos/test.mpg',
    metadata_per_frame=metadata,
    width=256,
    height=256,
    fps=30,
    backend='ffmpeg'  # Basic muxing, generic codec tags
)

print(f"Video: {result['video_path']}")
print(f"KLV file: {result['klv_path']}")
print(f"Frames: {result['num_frames']}")
```

## Modifying Existing Videos

Modify KLV metadata in existing videos (like `sample_video.mpg`) while preserving original video frames **losslessly** (no re-encoding).

### CLI Usage

```bash
# Lossless modification (default) - preserves original video frames exactly
vidmeta-modify input.mpg -o output.mpg --frame 5 --set latitude=37.5

# Output can be .mpg or .ts (both are MPEG-TS containers)
vidmeta-modify input.mpg -o output.ts --overrides changes.json

# Modify multiple frames and fields
vidmeta-modify input.mpg -o output.mpg \
  --frame 0 --set latitude=37.7 longitude=-122.4 \
  --frame 10 --set altitude=2000 heading=180

# Force re-encoding (lossy, but more flexible)
vidmeta-modify input.mpg -o output.ts --re-encode --frame 5 --set latitude=37.5
```

**Overrides JSON format:**

```json
{
  "0": { "latitude": 37.7749, "longitude": -122.4194 },
  "5": { "heading": 180.0 },
  "10": { "altitude": 2000.0, "pitch": -20.0 }
}
```

### Python API

```python
from vidmeta.video_modifier import modify_video_metadata

metadata_overrides = {
    0: {"latitude": 37.7749, "longitude": -122.4194},
    5: {"heading": 180.0, "pitch": -30.0},
    10: {"altitude": 2000.0}
}

# Lossless modification (default) - preserves original video frames
result = modify_video_metadata(
    input_video_path='videos/sample_video.mpg',
    output_video_path='videos/modified.mpg',  # Can use .mpg or .ts
    metadata_overrides=metadata_overrides,
    lossless=True  # Default - video frames pass through unchanged
)

# Or force re-encoding (lossy)
result = modify_video_metadata(
    input_video_path='videos/sample_video.mpg',
    output_video_path='videos/modified.ts',
    metadata_overrides=metadata_overrides,
    lossless=False,
    backend='gstreamer'
)
```

**How lossless mode works:**

- Uses GStreamer pipeline: `tsdemux ! h264parse ! mpegtsmux`
- Video stream passes through without decoding/re-encoding
- Only the KLV metadata stream is replaced
- Original video quality preserved exactly

**How re-encode mode works (lossless=False):**

- Extracts and decodes video frames
- Re-encodes with new KLV metadata
- Useful when video codec needs to change

**See also:** `examples/modify_sample_video.py` for a complete runnable example

## Testing

Run automated tests including round-trip validation:

```bash
uv run pytest tests/test_roundtrip.py -v
```

Tests include:

- Round-trip metadata preservation (extract and re-encode with no changes)
- Frame count validation
- Single field modification
- Multiple frame modifications

## Supported Metadata Fields

All optional (except `version`):

**Position**: `latitude`, `longitude`, `altitude`
**Orientation**: `heading`, `pitch`, `roll`
**Sensor**: `sensor_relative_azimuth`, `sensor_relative_elevation`, `sensor_relative_roll`
**FOV**: `horizontal_fov`, `vertical_fov`
**Range**: `slant_range`, `ground_range`, `target_width`
**Identification**: `mission_id`, `platform_call_sign`, `platform_designation`, `platform_tail_number`, `sensor_name`
**Other**: `platform_ground_speed`, `timestamp`, `version`

## Test Video Resources

Example videos with KLV metadata for testing:

- [Day Flight.mpg](http://samples.ffmpeg.org/MPEG2/mpegts-klv/Day%20Flight.mpg) - MPEG-TS with embedded KLV metadata from FFmpeg samples

### TeleSculptor Example Videos (VIRAT Dataset)

From the [TeleSculptor examples](https://github.com/Kitware/TeleSculptor/tree/master/examples):

- [09172008flight1tape3_2.mpg](https://data.kitware.com/#item/5ef11b419014a6d84ed53971) - The aircraft makes about one complete orbit over a site in Fort A.P. Hill, Virginia. The stare point remains fixed on the center of the scene and the field of view is quite narrow. The scene is composed primarily of buildings and vehicles.

- [09152008flight2tape2_4.mpg](https://data.kitware.com/#item/56f580488d777f753209c72f) - This is video of the same region but taken in a different style. The field of view is much larger and the stare point moves substantially. In addition to the buildings and vehicles which are the focus of the other clip, this video includes wide shots of roads and vegetation.
