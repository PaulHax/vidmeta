# KLV Test Videos

Generate test videos with KLV metadata streams for testing burnoutweb and KWIVER.

## Installation

```bash
cd klv-test-videos
uv pip install -e .
```

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

```python
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
