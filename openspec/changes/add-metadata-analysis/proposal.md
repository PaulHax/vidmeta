# Change: Add KLV Metadata Analysis and Export Tools

## Why

Developers need to reproduce bugs from classified UAV videos using unclassified test videos. Currently there's no way to:
1. Export raw KLV metadata for inspection (JSON/CSV)
2. Detect named patterns in metadata (e.g., "high-altitude", "missing-corners")

The analyst can share pattern names without revealing classified values, allowing developers to recreate bug-triggering conditions with `vidmeta-modify`.

## What Changes

- **Corner points support** - Add MISB ST 0601 corner point fields (tags 26-33, 82-89) to parsing/models
- **Metadata export** - New `vidmeta-dump` CLI to export metadata as JSON/CSV
- **Metadata analysis** - New `vidmeta-analyze` CLI to detect patterns and anomalies
- **Analysis models** - New Pydantic models for `FieldStats` and `AnalysisReport`

## Impact

- Affected specs: `corner-points` (new), `metadata-export` (new), `metadata-analysis` (new)
- Affected code:
  - `vidmeta/models.py` - Add corner point fields and analysis models
  - `vidmeta/klv_converter.py` - Add corner point mappings
  - `vidmeta/metadata_exporter.py` (new)
  - `vidmeta/metadata_analyzer.py` (new)
  - `vidmeta/patterns.py` (new)
  - `vidmeta/dump_cli.py` (new)
  - `vidmeta/analyze_cli.py` (new)
  - `pyproject.toml` - Add new entry points
