## ADDED Requirements

### Requirement: Field Statistics

The system SHALL compute statistics for each metadata field across all frames.

Statistics include:
- `present_ratio` - Percentage of frames containing this field
- `min_value`, `max_value`, `mean_value` - For numeric fields
- `has_discontinuities` - True if sudden jumps detected between consecutive frames
- `has_out_of_range` - True if values fall outside MISB ST 0601 valid ranges

#### Scenario: Compute numeric field stats

- **WHEN** `analyze_video()` processes a video with latitude values
- **THEN** the `FieldStats` for latitude SHALL include min, max, mean, and standard deviation

#### Scenario: Detect field discontinuities

- **WHEN** sensor_relative_elevation changes by more than 30 degrees between consecutive frames
- **THEN** the `FieldStats.has_discontinuities` SHALL be `True`

#### Scenario: Detect out-of-range values

- **WHEN** latitude value exceeds 90 degrees or is less than -90 degrees
- **THEN** the `FieldStats.has_out_of_range` SHALL be `True`

### Requirement: Pattern Detection

The system SHALL detect named metadata patterns and report matches.

Patterns include:
- `high-altitude` - Platform altitude exceeds 10000 meters
- `missing-corners` - No corner point fields present
- `missing-frame-center` - Frame center latitude/longitude absent
- `sensor-discontinuity` - Sudden jumps in sensor angles detected
- `partial-corners` - Some but not all corner point fields present

#### Scenario: Detect high altitude

- **WHEN** all altitude values in a video exceed 10000 meters
- **THEN** the `AnalysisReport.matched_templates` SHALL include `high-altitude`

#### Scenario: Detect missing corners

- **WHEN** no frames contain any corner point fields
- **THEN** the `AnalysisReport.matched_templates` SHALL include `missing-corners`

#### Scenario: Detect partial corners

- **WHEN** some frames have corner_lat_1 but no corner_lat_2
- **THEN** the `AnalysisReport.matched_templates` SHALL include `partial-corners`

### Requirement: Analysis Report

The system SHALL produce an analysis report containing frame count, field inventory, statistics, and pattern matches.

#### Scenario: Generate analysis report

- **WHEN** `analyze_video()` completes
- **THEN** the returned `AnalysisReport` SHALL contain:
  - `frame_count` - Total number of frames analyzed
  - `fields_present` - List of fields found in at least one frame
  - `fields_missing` - List of expected fields not found in any frame
  - `field_stats` - Dictionary of field name to `FieldStats`
  - `matched_templates` - List of detected pattern names
  - `anomalies` - List of human-readable anomaly descriptions

### Requirement: vidmeta-analyze CLI

The system SHALL provide a `vidmeta-analyze` command-line tool for metadata analysis.

#### Scenario: Analyze video with text output

- **WHEN** user runs `vidmeta-analyze video.mpg`
- **THEN** the system SHALL print a human-readable analysis report including frame count, fields present/missing, matched patterns, and anomalies

#### Scenario: Analyze video with JSON output

- **WHEN** user runs `vidmeta-analyze video.mpg --format json`
- **THEN** the system SHALL print the `AnalysisReport` as JSON

#### Scenario: Save analysis to file

- **WHEN** user runs `vidmeta-analyze video.mpg --output report.json`
- **THEN** the system SHALL write the analysis report to `report.json`
