## 1. Corner Points Support (Prerequisite)

- [ ] 1.1 Add corner point fields to `FrameMetadata` in `models.py` (corner_lat_1 through corner_lat_4, corner_lon_1 through corner_lon_4)
- [ ] 1.2 Add corner point mappings to `FIELD_MAPPINGS` in `klv_converter.py` (MISB tags 26-33)
- [ ] 1.3 Update `pydantic_to_flat_dict()` to include corner fields
- [ ] 1.4 Update `flat_dict_to_pydantic()` to include corner fields
- [ ] 1.5 Create `tests/test_corner_points.py` with unit tests for corner point parsing and round-trip
- [ ] 1.6 Run tests: `pytest tests/test_corner_points.py -v`

## 2. Metadata Export

- [ ] 2.1 Create `vidmeta/metadata_exporter.py` with `extract_all_metadata()`
- [ ] 2.2 Add `export_to_json()` function
- [ ] 2.3 Add `export_to_csv()` function
- [ ] 2.4 Create `tests/test_metadata_exporter.py` with unit tests for extraction and export functions
- [ ] 2.5 Run tests: `pytest tests/test_metadata_exporter.py -v`
- [ ] 2.6 Create `vidmeta/dump_cli.py` with argparse CLI
- [ ] 2.7 Add `vidmeta-dump` entry point to `pyproject.toml`
- [ ] 2.8 Manual test: `vidmeta-dump --help` and `vidmeta-dump sample_video.mpg --format json`

## 3. Analysis Models

- [ ] 3.1 Add `FieldStats` model to `models.py` (field_name, present, present_ratio, min/max/mean/std_dev, has_discontinuities, has_out_of_range)
- [ ] 3.2 Add `AnalysisReport` model to `models.py` (frame_count, fields_present/missing, field_stats, matched_templates, anomalies)
- [ ] 3.3 Create `tests/test_analysis_models.py` with unit tests for model instantiation and serialization
- [ ] 3.4 Run tests: `pytest tests/test_analysis_models.py -v`

## 4. Pattern Detection

- [ ] 4.1 Create `vidmeta/patterns.py` with `PATTERNS` dict containing named patterns:
  - `high-altitude` - Platform altitude > 10000m
  - `missing-corners` - Corner points absent
  - `missing-frame-center` - Frame center lat/lon absent
  - `sensor-discontinuity` - Sudden jumps in sensor angles
  - `partial-corners` - Some but not all corner points present
- [ ] 4.2 Implement `detect_patterns()` function
- [ ] 4.3 Create `tests/test_patterns.py` with unit tests for each pattern detector
- [ ] 4.4 Run tests: `pytest tests/test_patterns.py -v`

## 5. Metadata Analyzer

- [ ] 5.1 Create `vidmeta/metadata_analyzer.py` with `analyze_video()` function (stub returning empty report)
- [ ] 5.2 Implement field statistics computation (min/max/mean/stddev per field)
- [ ] 5.3 Add tests for field statistics to `tests/test_metadata_analyzer.py`
- [ ] 5.4 Run tests: `pytest tests/test_metadata_analyzer.py -v`
- [ ] 5.5 Implement discontinuity detection (sudden jumps between consecutive frames)
- [ ] 5.6 Add tests for discontinuity detection
- [ ] 5.7 Run tests: `pytest tests/test_metadata_analyzer.py -v`
- [ ] 5.8 Implement out-of-range detection (values outside MISB valid ranges)
- [ ] 5.9 Add tests for out-of-range detection
- [ ] 5.10 Run tests: `pytest tests/test_metadata_analyzer.py -v`
- [ ] 5.11 Implement `generate_report()` for text/JSON output
- [ ] 5.12 Add tests for report generation
- [ ] 5.13 Run tests: `pytest tests/test_metadata_analyzer.py -v`

## 6. Analyze CLI

- [ ] 6.1 Create `vidmeta/analyze_cli.py` with argparse CLI
- [ ] 6.2 Add `vidmeta-analyze` entry point to `pyproject.toml`
- [ ] 6.3 Manual test: `vidmeta-analyze --help` and `vidmeta-analyze sample_video.mpg`

## 7. Integration Tests

- [ ] 7.1 Create `tests/test_integration.py` with sample video fixture (reuse from test_roundtrip.py)
- [ ] 7.2 Integration test: `vidmeta-dump` JSON round-trip (dump → load JSON → verify structure)
- [ ] 7.3 Integration test: `vidmeta-dump` CSV round-trip (dump → load CSV → verify columns and row count)
- [ ] 7.4 Integration test: `vidmeta-analyze` pattern detection on sample video
- [ ] 7.5 Integration test: `vidmeta-analyze` JSON output structure validation
- [ ] 7.6 End-to-end workflow test: analyze → detect patterns → create overrides → modify video → re-analyze → verify pattern changed
- [ ] 7.7 Run all integration tests: `pytest tests/test_integration.py -v`

## 8. Documentation

- [ ] 8.1 Update README.md with new CLI commands and workflow example
- [ ] 8.2 Run full test suite: `pytest tests/ -v`
