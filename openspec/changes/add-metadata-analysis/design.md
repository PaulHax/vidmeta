## Context

This feature supports a workflow where analysts with access to classified UAV videos can detect metadata patterns and share pattern names (not values) with developers who then reproduce bugs using unclassified videos.

**Stakeholders:**
- Analysts: Run analysis on classified videos, share pattern names
- Developers: Create test videos matching patterns to reproduce bugs
- KWIVER team: Primary consumers of generated test videos

**Constraints:**
- Classified video values cannot be shared
- Only pattern names and structural descriptions are communicated
- Existing `vidmeta-modify` handles the actual video modification

## Goals / Non-Goals

**Goals:**
- Export metadata to JSON/CSV for manual inspection
- Detect named patterns automatically (high-altitude, missing-corners, etc.)
- Provide summary statistics without leaking exact values
- Support corner point fields (MISB ST 0601 tags 26-33, 82-89)

**Non-Goals:**
- Auto-generating override files (user creates manually based on patterns)
- Video content analysis (only metadata)
- Comparison between two videos (single-video analysis only)

## Decisions

**Decision: Single-video analysis (not comparison)**
- Rationale: Classified videos cannot be directly compared to unclassified ones
- The analyst shares pattern names verbally/textually, not through tooling

**Decision: Named patterns with lambda detectors**
- Each pattern has a name, description, and detection function
- Patterns are defined in `patterns.py` for easy extension
- Detection uses computed field statistics, not raw values

**Decision: Three output formats**
- JSON: Machine-readable, preserves structure
- CSV: Spreadsheet-friendly, flat structure
- Text: Human-readable summary with pattern matches

**Decision: Corner points as prerequisite**
- Many bugs involve missing/malformed corner points
- Adding these fields enables pattern detection for corner-related issues

## Data Flow

```
Video → ffmpeg extract KLV → parse_klv_file() → Dict[frame, metadata]
                                                        ↓
                                            ┌───────────┴───────────┐
                                            ↓                       ↓
                                    JSON/CSV export          Stats computation
                                    (vidmeta-dump)                  ↓
                                                            Pattern matching
                                                            (vidmeta-analyze)
```

## Risks / Trade-offs

**Risk: Pattern detection false positives**
- Mitigation: Patterns detect structural issues (missing fields) not value judgments
- User validates pattern matches against their understanding

**Risk: klvdata library limitations**
- Mitigation: Already handles MISB ST 0601; corner point tags are standard
- Unknown tags preserved via `_unknown_klv_tags` mechanism

**Trade-off: Stats vs exact values**
- Analysis reports include min/max/mean for context
- Analyst must judge whether to share these or just pattern names

## Open Questions

None currently - the plan document provides clear implementation guidance.
