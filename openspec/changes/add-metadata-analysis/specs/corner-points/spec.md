## ADDED Requirements

### Requirement: Corner Point Parsing

The system SHALL parse MISB ST 0601 corner point fields (tags 26-33) from KLV metadata packets.

Corner point fields:
- `corner_lat_1`, `corner_lon_1` - First corner latitude/longitude
- `corner_lat_2`, `corner_lon_2` - Second corner latitude/longitude
- `corner_lat_3`, `corner_lon_3` - Third corner latitude/longitude
- `corner_lat_4`, `corner_lon_4` - Fourth corner latitude/longitude

#### Scenario: Parse corner points from KLV packet

- **WHEN** a KLV packet contains corner latitude/longitude tags (MISB ST 0601 tags 26-33)
- **THEN** the parsed `FrameMetadata` model SHALL contain the corresponding `corner_lat_N` and `corner_lon_N` fields

#### Scenario: Absent corner points

- **WHEN** a KLV packet does not contain corner point tags
- **THEN** the parsed `FrameMetadata` model SHALL have `None` values for corner point fields

### Requirement: Corner Point Round-Trip

The system SHALL preserve corner point fields when converting between Pydantic models and flat dictionaries.

#### Scenario: Flat dict includes corner fields

- **WHEN** `pydantic_to_flat_dict()` is called on a `ParsedKLVPacket` with corner point data
- **THEN** the resulting flat dictionary SHALL include `corner_lat_1` through `corner_lat_4` and `corner_lon_1` through `corner_lon_4` keys

#### Scenario: Flat dict to Pydantic preserves corners

- **WHEN** `flat_dict_to_pydantic()` is called with corner point fields in the input dict
- **THEN** the resulting `FrameMetadata` SHALL contain the corner point values
