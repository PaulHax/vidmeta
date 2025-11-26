# vidmeta

Generate test videos with embedded geospatial and sensor metadata. Primarily used for testing KWIVER and related computer vision tools.

## Installation

GStreamer support is required for generating KWIVER-compatible videos with proper KLVA codec tags.

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install libgirepository1.0-dev gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-bad gstreamer1.0-plugins-good gstreamer1.0-openh264

# Install the package
pip install vidmeta
```

**Why GStreamer is required:**

- Proper KLVA codec tags (vs generic bin_data from FFmpeg)
- Correct running sum 16 checksums compatible with KWIVER
- All I-frames for full seeking support (forward and backward)
- KWIVER requires KLVA tags to recognize metadata streams

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

- `.ts` file - MPEG-TS video with embedded KLV data stream
- `.klv` file - Raw KLV packets for KWIVER testing (MISB ST 0601 format)

## Python API

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

Modify KLV metadata in existing videos (like `sample_video.mpg`) while preserving original video frames.

### CLI Usage

```bash
# Modify metadata using JSON file
vidmeta-modify input.mpg -o output.ts --overrides changes.json

# Modify single field on command line
vidmeta-modify input.mpg -o output.ts --frame 5 --set latitude=37.5

# Modify multiple frames and fields
vidmeta-modify input.mpg -o output.ts \
  --frame 0 --set latitude=37.7 longitude=-122.4 \
  --frame 10 --set altitude=2000 heading=180
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

# Define metadata changes for specific frames
metadata_overrides = {
    0: {"latitude": 37.7749, "longitude": -122.4194},
    5: {"heading": 180.0, "pitch": -30.0},
    10: {"altitude": 2000.0}
}

# Modify the video
result = modify_video_metadata(
    input_video_path='videos/sample_video.mpg',
    output_video_path='videos/modified.ts',
    metadata_overrides=metadata_overrides,
    backend='gstreamer'
)
```

**How it works:**

- Extracts KLV stream from input video using FFmpeg
- Parses KLV packets to extract existing metadata
- Merges your overrides with original metadata (field-level merge)
- Preserves original video frames (no re-encoding)
- Generates new video with modified metadata

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
