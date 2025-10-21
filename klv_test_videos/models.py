"""
Pydantic models for MISB ST 0601 KLV metadata.

This module defines type-safe, validated models for UAS metadata following
the MISB ST 0601 standard. The models are organized hierarchically to separate
platform, sensor, and frame-specific metadata.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class MetadataBase(BaseModel):
    """
    Base class for metadata models with shared configuration.

    Validation is disabled by default to allow degenerate/test values.
    Set validate_default=True when creating instances to enforce constraints.
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=False,
        validate_default=False,
    )


class PlatformMetadata(MetadataBase):
    """
    Platform-level metadata (aircraft/vehicle position and orientation).

    Attributes describe the UAS platform's location, heading, and movement.
    """

    mission_id: Optional[str] = None
    platform_designation: Optional[str] = None
    platform_call_sign: Optional[str] = None
    platform_tail_number: Optional[str] = None

    latitude: Optional[float] = Field(None, description="Platform latitude in degrees")
    longitude: Optional[float] = Field(
        None, description="Platform longitude in degrees"
    )
    altitude: Optional[float] = Field(
        None, description="Platform altitude in meters above MSL"
    )
    heading: Optional[float] = Field(
        None, description="Platform heading angle in degrees"
    )
    pitch: Optional[float] = Field(None, description="Platform pitch angle in degrees")
    roll: Optional[float] = Field(None, description="Platform roll angle in degrees")
    platform_ground_speed: Optional[float] = Field(
        None, description="Platform ground speed in m/s"
    )


class SensorMetadata(MetadataBase):
    """
    Sensor/gimbal metadata.

    Attributes describe the sensor's position relative to the platform,
    field of view, and range measurements.
    """

    sensor_name: Optional[str] = None
    sensor_relative_azimuth: Optional[float] = Field(
        None, description="Sensor azimuth relative to platform in degrees"
    )
    sensor_relative_elevation: Optional[float] = Field(
        None, description="Sensor elevation relative to platform in degrees"
    )
    sensor_relative_roll: Optional[float] = Field(
        None, description="Sensor roll relative to platform in degrees"
    )
    horizontal_fov: Optional[float] = Field(
        None, description="Horizontal field of view in degrees"
    )
    vertical_fov: Optional[float] = Field(
        None, description="Vertical field of view in degrees"
    )
    slant_range: Optional[float] = Field(
        None, description="Slant range to target in meters"
    )
    target_width: Optional[float] = Field(None, description="Target width in meters")
    ground_range: Optional[float] = Field(None, description="Ground range in meters")


class FrameMetadata(MetadataBase):
    """
    Per-frame metadata.

    Attributes describe the center point of the image frame on the ground.
    """

    frame_center_latitude: Optional[float] = Field(
        None, description="Frame center latitude in degrees"
    )
    frame_center_longitude: Optional[float] = Field(
        None, description="Frame center longitude in degrees"
    )
    frame_center_elevation: Optional[float] = Field(
        None, description="Frame center elevation in meters"
    )


class KLVMetadata(MetadataBase):
    """
    Complete KLV metadata packet.

    Top-level model containing timestamp, version, and nested metadata
    for platform, sensor, and frame information.
    """

    timestamp: Optional[datetime] = Field(
        None, description="Precision timestamp or event start time"
    )
    version: Optional[int] = Field(None, description="UAS Datalink LS version number")

    platform: PlatformMetadata = Field(
        default_factory=PlatformMetadata, description="Platform-level metadata"
    )
    sensor: SensorMetadata = Field(
        default_factory=SensorMetadata, description="Sensor/gimbal metadata"
    )
    frame: FrameMetadata = Field(
        default_factory=FrameMetadata, description="Frame-specific metadata"
    )


class ParsedKLVPacket(BaseModel):
    """
    Container for parsed KLV metadata with raw bytes stored separately.

    This separates the concern of structured metadata from raw packet storage,
    allowing for clean type-safe metadata access while preserving the original
    bytes for pass-through or re-encoding scenarios.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True, validate_assignment=False, validate_default=False
    )

    metadata: KLVMetadata = Field(description="Structured metadata parsed from packet")
    raw_packet: bytes = Field(description="Original raw KLV packet bytes")
