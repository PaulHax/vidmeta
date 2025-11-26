# Project Context

## Purpose

vidmeta is a Python library for parsing, analyzing, and generating test videos with embedded geospatial and sensor metadata following the MISB ST 0601 KLV standard. It is primarily used for testing KWIVER and related computer vision tools that process UAV/aerial video footage.

Key capabilities:
- Parse KLV metadata packets into typed Pydantic models
- Generate test videos with embedded KLV data streams
- Modify existing videos losslessly (preserve original video frames while replacing metadata)
- Support for MISB ST 0601 compliant metadata including platform position, sensor orientation, and frame geolocation

## Tech Stack

- **Python 3.10+** - Core language
- **Pydantic 2.0+** - Data validation and typed models for KLV metadata
- **klvdata** - KLV packet encoding/decoding
- **GStreamer** (via PyGObject) - Video muxing with proper KLVA codec tags
- **OpenCV** - Video frame extraction and manipulation
- **NumPy** - Array operations for video processing
- **pytest** - Testing framework
- **ruff** - Linting and formatting

## Project Conventions

### Code Style

- Prefer functional programming paradigm
- Use type hints throughout
- No comments unless code is cryptic
- Use ruff for linting/formatting

### Architecture Patterns

- **Pydantic models** (`models.py`) - Type-safe metadata representation with hierarchical structure (Platform, Sensor, Frame metadata)
- **Backend abstraction** - Video generation supports multiple backends (GStreamer preferred, FFmpeg fallback)
- **CLI + API** - Both command-line tools and Python API for all operations
- **Optional dependencies** - Core parsing has minimal deps; video muxing is optional (`[mux]` extra)

### Testing Strategy

- Tests in `tests/` directory
- pytest with fixtures for downloading sample videos
- Round-trip tests verify metadata preservation
- Frame hash comparison for lossless verification
- Run with: `uv run pytest tests/ -v`

### Git Workflow

- Small commits with concise one-line messages
- No backwards compatibility needed - just refactor all usages

## Domain Context

- **MISB ST 0601** - Military standard for UAS (drone) metadata encoding
- **KLV** - Key-Length-Value encoding format used in MPEG-TS streams
- **KLVA codec tags** - Required by KWIVER to recognize metadata streams (FFmpeg cannot set these)
- **MPEG-TS** - Transport stream container format (.ts or .mpg extension)
- **Platform metadata** - Aircraft position (lat/lon/alt), heading, pitch, roll
- **Sensor metadata** - Gimbal angles, FOV, slant range
- **Frame metadata** - Ground footprint center coordinates

## Important Constraints

- GStreamer required for proper KLVA codec tags (FFmpeg creates generic "bin_data" streams)
- PyGObject version must be <3.51.0 for girepository-1.0 compatibility
- System GStreamer packages required (cannot be pip-installed)
- Lossless video modification uses passthrough pipeline - no re-encoding

## External Dependencies

- **GStreamer** - System package for video muxing (`gstreamer1.0-plugins-bad` for `mpegtsmux`)
- **klvdata** - PyPI package for KLV encoding/decoding
- **Sample videos** - Downloaded from data.kitware.com for testing
- **KWIVER** - The primary consumer of generated test videos (separate project)
