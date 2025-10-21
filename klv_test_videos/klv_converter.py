"""
Converter functions between klvdata and Pydantic models.

This module bridges the klvdata library (raw KLV parsing) with the
type-safe Pydantic models defined in models.py.
"""

from typing import Dict, Any, Tuple
from datetime import datetime

from klvdata import misb0601

from .models import (
    KLVMetadata,
    ParsedKLVPacket,
    PlatformMetadata,
    SensorMetadata,
    FrameMetadata,
)


def _tag_key_to_num(tag_key: bytes) -> int:
    """Convert tag key bytes to tag number."""
    return int.from_bytes(tag_key, "big")


def _extract_unknown_tags(raw_packet: bytes) -> Dict[str, bytes]:
    """
    Extract unknown KLV tags from a raw packet.

    Args:
        raw_packet: Raw KLV packet bytes

    Returns:
        Dictionary mapping tag hex strings to raw tag bytes
    """
    uas_set = misb0601.UASLocalMetadataSet(raw_packet)
    metadata_dict = uas_set.MetadataList()

    # Build set of known tag numbers
    known_tag_numbers = set(metadata_dict.keys())

    unknown_tags = {}
    for tag_key, element in uas_set.items.items():
        tag_num = _tag_key_to_num(tag_key)

        # Skip tags we've already processed (tag 1 = checksum)
        if tag_num not in known_tag_numbers and tag_num != 1:
            unknown_tags[tag_key.hex()] = bytes(element)

    return unknown_tags


# Mapping from MISB field names to (section, field_name, type_converter)
FIELD_MAPPINGS = {
    # Platform fields
    "Mission ID": ("platform", "mission_id", str),
    "Platform Designation": ("platform", "platform_designation", str),
    "Platform Call Sign": ("platform", "platform_call_sign", str),
    "Platform Tail Number": ("platform", "platform_tail_number", str),
    "Sensor Latitude": ("platform", "latitude", float),
    "Sensor Longitude": ("platform", "longitude", float),
    "Sensor True Altitude": ("platform", "altitude", float),
    "Platform Heading Angle": ("platform", "heading", float),
    "Platform Pitch Angle": ("platform", "pitch", float),
    "Platform Roll Angle": ("platform", "roll", float),
    "Platform Ground Speed": ("platform", "platform_ground_speed", float),
    # Sensor fields
    "Image Source Sensor": ("sensor", "sensor_name", str),
    "Sensor Relative Azimuth Angle": ("sensor", "sensor_relative_azimuth", float),
    "Sensor Relative Elevation Angle": ("sensor", "sensor_relative_elevation", float),
    "Sensor Relative Roll Angle": ("sensor", "sensor_relative_roll", float),
    "Sensor Horizontal Field of View": ("sensor", "horizontal_fov", float),
    "Sensor Vertical Field of View": ("sensor", "vertical_fov", float),
    "Slant Range": ("sensor", "slant_range", float),
    "Target Width": ("sensor", "target_width", float),
    "Ground Range": ("sensor", "ground_range", float),
    # Frame fields
    "Frame Center Latitude": ("frame", "frame_center_latitude", float),
    "Frame Center Longitude": ("frame", "frame_center_longitude", float),
    "Frame Center Elevation": ("frame", "frame_center_elevation", float),
}


def parse_klv_packet_to_pydantic(packet: bytes) -> ParsedKLVPacket:
    """
    Parse a KLV packet into a Pydantic model with separate raw packet storage.

    Args:
        packet: Raw KLV packet bytes

    Returns:
        ParsedKLVPacket containing structured metadata and raw bytes
    """
    # Parse using klvdata
    uas_set = misb0601.UASLocalMetadataSet(packet)
    metadata_dict = uas_set.MetadataList()

    # Build nested dict for Pydantic model
    parsed = {"platform": {}, "sensor": {}, "frame": {}}

    # Extract all tag numbers we know about (for unknown tag detection)
    known_tag_numbers = set()

    for tag_num, tag_info in metadata_dict.items():
        name = tag_info[0]  # First element is the name
        value_str = tag_info[3]  # Fourth element is the value as string
        known_tag_numbers.add(tag_num)

        # Handle timestamps specially
        if name in ("Precision Time Stamp", "Event Start Time - UTC"):
            try:
                # klvdata returns ISO format like '2015-10-07 07:18:02.380305+00:00'
                parsed["timestamp"] = datetime.fromisoformat(value_str)
            except (ValueError, OSError):
                # If parsing fails, keep as string (for degenerate test cases)
                parsed["timestamp"] = value_str
            continue

        # Handle version
        if name == "UAS Datalink LS Version Number":
            try:
                parsed["version"] = int(float(value_str))
            except (ValueError, TypeError):
                parsed["version"] = value_str  # Allow degenerate values
            continue

        # Map other fields using mapping table
        if name in FIELD_MAPPINGS:
            section, field, type_func = FIELD_MAPPINGS[name]
            try:
                parsed[section][field] = type_func(value_str)
            except (ValueError, TypeError):
                # For degenerate test values, store as string
                parsed[section][field] = value_str

    # Create Pydantic models
    metadata = KLVMetadata(
        timestamp=parsed.get("timestamp"),
        version=parsed.get("version"),
        platform=PlatformMetadata(**parsed["platform"]),
        sensor=SensorMetadata(**parsed["sensor"]),
        frame=FrameMetadata(**parsed["frame"]),
    )

    return ParsedKLVPacket(metadata=metadata, raw_packet=packet)


def pydantic_to_flat_dict(
    parsed: ParsedKLVPacket, include_unknown_tags: bool = True
) -> Tuple[Dict[str, Any], bytes, Dict[str, bytes]]:
    """
    Convert a ParsedKLVPacket to a flat dict (backward compatibility).

    Args:
        parsed: ParsedKLVPacket instance
        include_unknown_tags: If True, extract and return unknown KLV tags

    Returns:
        Tuple of (flat_dict, raw_packet, unknown_tags) where:
        - flat_dict contains all known fields at top level
        - raw_packet is the original bytes
        - unknown_tags is a dict of {tag_hex: tag_bytes} for unknown tags
    """
    metadata = parsed.metadata

    # Build result dict, excluding None values from the start
    result = {
        k: v
        for k, v in {
            "timestamp": metadata.timestamp,
            "version": metadata.version,
            # Platform fields
            "mission_id": metadata.platform.mission_id,
            "platform_designation": metadata.platform.platform_designation,
            "platform_call_sign": metadata.platform.platform_call_sign,
            "platform_tail_number": metadata.platform.platform_tail_number,
            "latitude": metadata.platform.latitude,
            "longitude": metadata.platform.longitude,
            "altitude": metadata.platform.altitude,
            "heading": metadata.platform.heading,
            "pitch": metadata.platform.pitch,
            "roll": metadata.platform.roll,
            "platform_ground_speed": metadata.platform.platform_ground_speed,
            # Sensor fields
            "sensor_name": metadata.sensor.sensor_name,
            "sensor_relative_azimuth": metadata.sensor.sensor_relative_azimuth,
            "sensor_relative_elevation": metadata.sensor.sensor_relative_elevation,
            "sensor_relative_roll": metadata.sensor.sensor_relative_roll,
            "horizontal_fov": metadata.sensor.horizontal_fov,
            "vertical_fov": metadata.sensor.vertical_fov,
            "slant_range": metadata.sensor.slant_range,
            "target_width": metadata.sensor.target_width,
            "ground_range": metadata.sensor.ground_range,
            # Frame fields
            "frame_center_latitude": metadata.frame.frame_center_latitude,
            "frame_center_longitude": metadata.frame.frame_center_longitude,
            "frame_center_elevation": metadata.frame.frame_center_elevation,
        }.items()
        if v is not None
    }

    # Extract unknown tags if requested
    unknown_tags = _extract_unknown_tags(parsed.raw_packet) if include_unknown_tags else {}

    return result, parsed.raw_packet, unknown_tags


def flat_dict_to_pydantic(
    flat_dict: Dict[str, Any], raw_packet: bytes = None
) -> ParsedKLVPacket:
    """
    Convert a flat dict (old format) to ParsedKLVPacket (new format).

    Args:
        flat_dict: Dictionary with flat keys like 'latitude', 'sensor_name', etc.
        raw_packet: Optional raw packet bytes

    Returns:
        ParsedKLVPacket instance
    """
    # Build nested structure
    parsed = {
        "timestamp": flat_dict.get("timestamp"),
        "version": flat_dict.get("version"),
        "platform": {
            "mission_id": flat_dict.get("mission_id"),
            "platform_designation": flat_dict.get("platform_designation"),
            "platform_call_sign": flat_dict.get("platform_call_sign"),
            "platform_tail_number": flat_dict.get("platform_tail_number"),
            "latitude": flat_dict.get("latitude"),
            "longitude": flat_dict.get("longitude"),
            "altitude": flat_dict.get("altitude"),
            "heading": flat_dict.get("heading"),
            "pitch": flat_dict.get("pitch"),
            "roll": flat_dict.get("roll"),
            "platform_ground_speed": flat_dict.get("platform_ground_speed"),
        },
        "sensor": {
            "sensor_name": flat_dict.get("sensor_name"),
            "sensor_relative_azimuth": flat_dict.get("sensor_relative_azimuth"),
            "sensor_relative_elevation": flat_dict.get("sensor_relative_elevation"),
            "sensor_relative_roll": flat_dict.get("sensor_relative_roll"),
            "horizontal_fov": flat_dict.get("horizontal_fov"),
            "vertical_fov": flat_dict.get("vertical_fov"),
            "slant_range": flat_dict.get("slant_range"),
            "target_width": flat_dict.get("target_width"),
            "ground_range": flat_dict.get("ground_range"),
        },
        "frame": {
            "frame_center_latitude": flat_dict.get("frame_center_latitude"),
            "frame_center_longitude": flat_dict.get("frame_center_longitude"),
            "frame_center_elevation": flat_dict.get("frame_center_elevation"),
        },
    }

    metadata = KLVMetadata(
        timestamp=parsed.get("timestamp"),
        version=parsed.get("version"),
        platform=PlatformMetadata(**parsed["platform"]),
        sensor=SensorMetadata(**parsed["sensor"]),
        frame=FrameMetadata(**parsed["frame"]),
    )

    return ParsedKLVPacket(
        metadata=metadata, raw_packet=raw_packet if raw_packet is not None else b""
    )
