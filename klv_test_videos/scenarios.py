"""Pre-defined test scenarios for generating KLV test videos."""

from datetime import datetime, timezone
from typing import List, Dict, Any


def sample_video_middle_metadata() -> List[Dict[str, Any]]:
    """
    Generate metadata matching the middle frames of burnoutweb/test-videos/sample_video.mpg.

    This creates 10 frames with metadata values from frame 812 of the sample video:
    - Position: Adelaide, Australia area (lat=-34.974, lon=138.486, alt=4904m)
    - Heading: 321.921°, Pitch: 3.35154°, Roll: 8.84426°
    - Sensor FOV: H=0.914626°, V=0.513619°
    - Slant Range: 7890.99m
    - Mission: Tabasco-2015-Oct-07-0449

    Returns:
        List of 10 metadata dictionaries
    """
    base_metadata = {
        'version': 7,
        'mission_id': 'Tabasco-2015-Oct-07-0449',
        'platform_tail_number': 'VH-EMI',
        'platform_designation': 'Beechcraft 1900C',
        'platform_call_sign': 'EMI',
        'sensor_name': 'MX-20HD EON COL',
        'latitude': -34.974211466021004,
        'longitude': 138.48646995541009,
        'altitude': 4904.0527962157621,
        'heading': 321.921,
        'pitch': 3.35154,
        'roll': 8.84426,
        'sensor_relative_azimuth': 91.2416,
        'sensor_relative_elevation': -29.4914,
        'sensor_relative_roll': 0.0326901,
        'horizontal_fov': 0.914626,
        'vertical_fov': 0.513619,
        'slant_range': 7890.99,
        'target_width': 125.887,
        'ground_range': 6189.58,
        'platform_ground_speed': 89,
    }

    # Create 10 frames with small variations
    metadata_list = []
    base_timestamp = 1444202320413948  # Unix microseconds from sample

    for i in range(10):
        frame_meta = base_metadata.copy()

        # Add timestamp (incremented by 40ms per frame for 25 fps)
        frame_meta['timestamp'] = base_timestamp + (i * 40_000)

        # Add small variations to simulate camera movement
        frame_meta['heading'] += i * 0.1
        frame_meta['pitch'] += i * 0.01
        frame_meta['roll'] -= i * 0.02
        frame_meta['latitude'] += i * 0.00001
        frame_meta['longitude'] += i * 0.00001
        frame_meta['altitude'] += i * 0.5

        metadata_list.append(frame_meta)

    return metadata_list


def stationary_camera(num_frames: int = 30) -> List[Dict[str, Any]]:
    """
    Generate metadata for a stationary camera.

    Args:
        num_frames: Number of frames to generate

    Returns:
        List of metadata dictionaries
    """
    base_time = datetime.now(timezone.utc)

    metadata_list = []
    for i in range(num_frames):
        metadata_list.append({
            'timestamp': base_time.timestamp() * 1_000_000 + (i * 33_333),  # 30 fps
            'mission_id': 'STATIONARY_TEST',
            'latitude': 37.7749,
            'longitude': -122.4194,
            'altitude': 500.0,
            'heading': 90.0,
            'pitch': -45.0,
            'roll': 0.0,
            'horizontal_fov': 60.0,
            'vertical_fov': 45.0,
            'slant_range': 1000.0,
        })

    return metadata_list


def moving_camera_path(num_frames: int = 60) -> List[Dict[str, Any]]:
    """
    Generate metadata for a camera moving along a path.

    Args:
        num_frames: Number of frames to generate

    Returns:
        List of metadata dictionaries
    """
    base_time = datetime.now(timezone.utc)

    # Start and end positions
    start_lat, end_lat = 37.7749, 37.8049
    start_lon, end_lon = -122.4194, -122.3894
    start_alt, end_alt = 300.0, 800.0
    start_heading, end_heading = 45.0, 225.0

    metadata_list = []
    for i in range(num_frames):
        t = i / (num_frames - 1) if num_frames > 1 else 0

        metadata_list.append({
            'timestamp': base_time.timestamp() * 1_000_000 + (i * 33_333),
            'mission_id': 'MOVING_TEST',
            'latitude': start_lat + (end_lat - start_lat) * t,
            'longitude': start_lon + (end_lon - start_lon) * t,
            'altitude': start_alt + (end_alt - start_alt) * t,
            'heading': start_heading + (end_heading - start_heading) * t,
            'pitch': -20.0 + 15.0 * t,
            'roll': 10.0 * t,
            'horizontal_fov': 70.0,
            'vertical_fov': 50.0,
            'slant_range': 6000.0 - 3000.0 * t,
        })

    return metadata_list


def high_altitude_survey(num_frames: int = 30) -> List[Dict[str, Any]]:
    """
    Generate metadata for a high-altitude survey camera.

    Args:
        num_frames: Number of frames to generate

    Returns:
        List of metadata dictionaries
    """
    base_time = datetime.now(timezone.utc)

    metadata_list = []
    for i in range(num_frames):
        metadata_list.append({
            'timestamp': base_time.timestamp() * 1_000_000 + (i * 33_333),
            'mission_id': 'HIGH_ALT_SURVEY',
            'latitude': 37.7749 + i * 0.0001,
            'longitude': -122.4194 + i * 0.0001,
            'altitude': 5000.0,
            'heading': 180.0,
            'pitch': -80.0,
            'roll': 0.0,
            'horizontal_fov': 90.0,
            'vertical_fov': 70.0,
            'slant_range': 15000.0,
        })

    return metadata_list


def minimal_metadata(num_frames: int = 10) -> List[Dict[str, Any]]:
    """
    Generate minimal metadata (only mandatory fields).

    Args:
        num_frames: Number of frames to generate

    Returns:
        List of metadata dictionaries
    """
    base_time = datetime.now(timezone.utc)

    metadata_list = []
    for i in range(num_frames):
        metadata_list.append({
            'timestamp': base_time.timestamp() * 1_000_000 + (i * 33_333),
            'mission_id': 'MINIMAL_TEST',
        })

    return metadata_list


# Scenario registry
SCENARIOS = {
    'sample_video': {
        'name': 'Sample Video Match',
        'description': '10 frames matching sample_video.mpg middle frames (frame 812)',
        'generator': sample_video_middle_metadata,
        'default_output': 'videos/test_sample_match.mpg',
    },
    'stationary': {
        'name': 'Stationary Camera',
        'description': 'Fixed camera position and orientation',
        'generator': stationary_camera,
        'default_output': 'videos/test_stationary.mpg',
    },
    'moving': {
        'name': 'Moving Camera Path',
        'description': 'Camera moving along a defined path',
        'generator': moving_camera_path,
        'default_output': 'videos/test_moving.mpg',
    },
    'high_altitude': {
        'name': 'High Altitude Survey',
        'description': 'High-altitude camera with downward view',
        'generator': high_altitude_survey,
        'default_output': 'videos/test_high_alt.mpg',
    },
    'minimal': {
        'name': 'Minimal Metadata',
        'description': 'Only mandatory KLV fields',
        'generator': minimal_metadata,
        'default_output': 'videos/test_minimal.mpg',
    },
}


def get_scenario(name: str) -> Dict[str, Any]:
    """Get scenario by name."""
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}. Available: {list(SCENARIOS.keys())}")
    return SCENARIOS[name]


def list_scenarios() -> List[str]:
    """List all available scenario names."""
    return list(SCENARIOS.keys())
