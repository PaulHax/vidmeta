## ADDED Requirements

### Requirement: Metadata Extraction

The system SHALL extract all KLV metadata from a video file into a frame-indexed data structure.

#### Scenario: Extract metadata from video

- **WHEN** `extract_all_metadata()` is called with a valid video path
- **THEN** the system SHALL return a dictionary mapping frame numbers to `ParsedKLVPacket` instances

#### Scenario: Video without KLV stream

- **WHEN** `extract_all_metadata()` is called on a video without a KLV data stream
- **THEN** the system SHALL return an empty dictionary

### Requirement: JSON Export

The system SHALL export extracted metadata to JSON format.

#### Scenario: Export to JSON file

- **WHEN** `export_to_json()` is called with metadata and an output path
- **THEN** the system SHALL write a JSON file containing all frame metadata with nested structure (platform, sensor, frame)

#### Scenario: JSON preserves types

- **WHEN** metadata contains datetime timestamps
- **THEN** the JSON export SHALL serialize timestamps as ISO 8601 strings

### Requirement: CSV Export

The system SHALL export extracted metadata to CSV format with flattened columns.

#### Scenario: Export to CSV file

- **WHEN** `export_to_csv()` is called with metadata and an output path
- **THEN** the system SHALL write a CSV file with one row per frame and columns for each metadata field

#### Scenario: CSV column ordering

- **WHEN** metadata is exported to CSV
- **THEN** the first column SHALL be `frame_number` followed by alphabetically sorted field names

### Requirement: vidmeta-dump CLI

The system SHALL provide a `vidmeta-dump` command-line tool for metadata export.

#### Scenario: Dump to JSON

- **WHEN** user runs `vidmeta-dump video.mpg --format json --output metadata.json`
- **THEN** the system SHALL extract KLV metadata and write it to `metadata.json` in JSON format

#### Scenario: Dump to CSV

- **WHEN** user runs `vidmeta-dump video.mpg --format csv --output metadata.csv`
- **THEN** the system SHALL extract KLV metadata and write it to `metadata.csv` in CSV format

#### Scenario: Default format

- **WHEN** user runs `vidmeta-dump video.mpg` without specifying format
- **THEN** the system SHALL default to JSON format and print to stdout
