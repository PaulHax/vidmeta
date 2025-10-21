# klvhax

Generate test videos with KLV metadata streams for testing burnoutweb and KWIVER.

## Installation

### Basic Installation (FFmpeg-based)

```bash
cd klvhax
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
# Generate video matching sample_video.mpg frame 812 (uses GStreamer by default)
generate-klv-video sample_video

# Use FFmpeg backend instead
generate-klv-video sample_video --backend ffmpeg

# List available scenarios
generate-klv-video --list

# Generate all scenarios
generate-klv-video --all

# Custom output and size
generate-klv-video moving --output videos/my_test.ts --width 256 --height 256

# Specify backend explicitly
generate-klv-video moving --backend gstreamer --width 256 --height 256
```

Available scenarios: `sample_video`, `stationary`, `moving`, `high_altitude`, `minimal`

Each generates:

- `.mpg` file - MPEG-TS video with embedded KLV data stream
- `.klv` file - Raw KLV packets (use this for KWIVER testing)

**Note**: The KLV data is embedded in the MPEG-TS stream, but FFmpeg cannot replicate the full KLVA codec tagging found in professional tools. For reliable KWIVER testing, use the separate `.klv` file which contains properly formatted MISB ST 0601 packets.

## Python API

Unified API with backend selection (see `examples/example_gstreamer.py` for complete runnable example):

```python
from datetime import datetime, timezone
from klv_test_videos.video_builder import build_klv_video

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
modify-klv-video input.mpg -o output.ts --overrides changes.json

# Modify single field on command line
modify-klv-video input.mpg -o output.ts --frame 5 --set latitude=37.5

# Modify multiple frames and fields
modify-klv-video input.mpg -o output.ts \
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
from klv_test_videos.video_modifier import modify_video_metadata

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
pytest tests/test_roundtrip.py -v
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
