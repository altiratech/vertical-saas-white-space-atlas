# Vertical SaaS White-Space Atlas

Vertical SaaS White-Space Atlas is a standalone repo scaffold hydrated from the Karpathy1 materials.

## Product Center

Build a ranked market-selection engine for boring, fragmented industries using public business-demography and labor data.

The founding loop is:
1. ingest public industry and labor anchors
2. normalize one inspectable industry table
3. score likely software and roll-up wedges
4. show evidence-backed ranked output

## Current Repo Status

This repo now contains the first real-data slice:
- a Python build that fetches official CBP, SBA, BLS, and Census crosswalk artifacts
- an added workflow layer from the BLS National Employment Matrix plus O*NET work activities
- a normalized 6-digit national NAICS table in `clean/`
- scored industry cells in `data/`
- a static explorer payload and plain HTML surface in `site/`

## Canonical Build Truth

Treat these docs as authoritative:
- `docs/FOUNDING_PACKET.md`
- `docs/DEVELOPMENT_PACKET.md`
- `docs/BOOTSTRAP.md`
- `docs/FIRST_SLICE.md`
- `docs/IMPLEMENTATION_ENTRY_BRIEF.md`
- `docs/ARCHITECTURE_GUARDRAILS.md`

## Planned Repo Shape

- `raw/`
  - cached public source pulls
- `clean/`
  - normalized descriptions and lookup tables
- `data/`
  - merged intermediate tables and scoring outputs
- `site/`
  - static explorer
- `prompts/`
  - scoring prompts and rubric contracts
- `schemas/`
  - entity and score schemas
- `scripts/`
  - fetch, normalize, score, and publish helpers
- `docs/`
  - build truth and guardrails
- `tests/`
  - schema, scoring, and pipeline coverage

## Build Rule

Do not drift into a broad market-intelligence platform before the ranked move engine works.

## First Slice Build

Run the first slice end to end with:

```bash
python3 scripts/build_first_slice.py
```

Outputs land in:
- `raw/` for cached source artifacts
- `clean/` for normalized tables
- `data/` for scored exports
- `site/data.json` for the static explorer payload
- `site/index.html` for the minimal explorer surface
