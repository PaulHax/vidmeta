"""Test Pydantic models and converters."""

from datetime import datetime

from kwiver_testdata.models import (
    KLVMetadata,
    PlatformMetadata,
    SensorMetadata,
    FrameMetadata,
    ParsedKLVPacket,
)
from kwiver_testdata.klv_converter import (
    flat_dict_to_pydantic,
    pydantic_to_flat_dict,
)


def test_platform_metadata_creation():
    """Test creating PlatformMetadata with valid values."""
    platform = PlatformMetadata(
        latitude=37.7749,
        longitude=-122.4194,
        altitude=100.0,
        heading=45.0,
    )

    assert platform.latitude == 37.7749
    assert platform.longitude == -122.4194
    assert platform.altitude == 100.0
    assert platform.heading == 45.0


def test_platform_metadata_degenerate_values():
    """Test that degenerate values are allowed for testing."""
    # For degenerate test values, use model_construct() which bypasses validation
    platform = PlatformMetadata.model_construct(
        latitude=999.0,  # Invalid latitude
        longitude=500.0,  # Invalid longitude
        heading=-45.0,  # Invalid heading (should be 0-360)
    )

    assert platform.latitude == 999.0
    assert platform.longitude == 500.0
    assert platform.heading == -45.0


def test_klv_metadata_nested_structure():
    """Test KLVMetadata with nested platform, sensor, frame."""
    metadata = KLVMetadata(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        version=1,
        platform=PlatformMetadata(latitude=40.0, longitude=-75.0),
        sensor=SensorMetadata(sensor_name="Test Sensor"),
        frame=FrameMetadata(frame_center_latitude=40.5),
    )

    assert metadata.timestamp.year == 2024
    assert metadata.version == 1
    assert metadata.platform.latitude == 40.0
    assert metadata.sensor.sensor_name == "Test Sensor"
    assert metadata.frame.frame_center_latitude == 40.5


def test_parsed_klv_packet():
    """Test ParsedKLVPacket separates metadata from raw bytes."""
    metadata = KLVMetadata(platform=PlatformMetadata(latitude=37.0, longitude=-122.0))
    raw_packet = b"\x01\x02\x03\x04"

    parsed = ParsedKLVPacket(metadata=metadata, raw_packet=raw_packet)

    assert parsed.metadata.platform.latitude == 37.0
    assert parsed.raw_packet == b"\x01\x02\x03\x04"


def test_flat_dict_to_pydantic_conversion():
    """Test converting flat dict (old format) to Pydantic models."""
    flat_dict = {
        "timestamp": datetime(2024, 1, 1, 12, 0, 0),
        "version": 1,
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 100.0,
        "sensor_name": "Test Camera",
        "frame_center_latitude": 37.8,
    }

    parsed = flat_dict_to_pydantic(flat_dict, raw_packet=b"test")

    assert parsed.metadata.timestamp.year == 2024
    assert parsed.metadata.version == 1
    assert parsed.metadata.platform.latitude == 37.7749
    assert parsed.metadata.platform.longitude == -122.4194
    assert parsed.metadata.platform.altitude == 100.0
    assert parsed.metadata.sensor.sensor_name == "Test Camera"
    assert parsed.metadata.frame.frame_center_latitude == 37.8
    assert parsed.raw_packet == b"test"


def test_pydantic_to_flat_dict_conversion():
    """Test converting Pydantic models back to flat dict."""
    parsed = ParsedKLVPacket(
        metadata=KLVMetadata(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            version=1,
            platform=PlatformMetadata(
                latitude=37.7749,
                longitude=-122.4194,
                altitude=100.0,
            ),
            sensor=SensorMetadata(sensor_name="Test Camera"),
            frame=FrameMetadata(frame_center_latitude=37.8),
        ),
        raw_packet=b"test",
    )

    flat_dict, raw_packet, unknown_tags = pydantic_to_flat_dict(parsed)

    assert flat_dict["timestamp"].year == 2024
    assert flat_dict["version"] == 1
    assert flat_dict["latitude"] == 37.7749
    assert flat_dict["longitude"] == -122.4194
    assert flat_dict["altitude"] == 100.0
    assert flat_dict["sensor_name"] == "Test Camera"
    assert flat_dict["frame_center_latitude"] == 37.8
    assert raw_packet == b"test"


def test_round_trip_conversion():
    """Test that flat_dict -> pydantic -> flat_dict preserves data."""
    original = {
        "timestamp": datetime(2024, 1, 1, 12, 0, 0),
        "latitude": 37.7749,
        "longitude": -122.4194,
        "sensor_name": "Test",
    }

    # Convert to Pydantic
    parsed = flat_dict_to_pydantic(original)

    # Convert back to flat dict
    result, _, _ = pydantic_to_flat_dict(parsed)

    assert result["timestamp"] == original["timestamp"]
    assert result["latitude"] == original["latitude"]
    assert result["longitude"] == original["longitude"]
    assert result["sensor_name"] == original["sensor_name"]


def test_empty_metadata():
    """Test creating empty metadata structures."""
    metadata = KLVMetadata()

    assert metadata.timestamp is None
    assert metadata.version is None
    assert metadata.platform.latitude is None
    assert metadata.sensor.sensor_name is None
    assert metadata.frame.frame_center_latitude is None
