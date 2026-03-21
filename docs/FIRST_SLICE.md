# Vertical SaaS White-Space Atlas First Slice

Status: locked kickoff slice

## Goal

Publish a national-only, 6-digit-NAICS static explorer that scores industries using CBP, SBA, and BLS inputs.

## Locked Decisions

- Geography: national only.
- Industry granularity: 6-digit NAICS.
- First source set:
  - Census County Business Patterns
  - SBA size standards
  - BLS employment or projection data
- First UI mode: static explorer only.

## First Files To Touch

- `schemas/`
- `scripts/`
- `data/`
- `site/`
- `tests/`

## Done When

- one normalized industry table exists
- scores are inspectable and evidence-backed
- `site/data.json` powers a useful ranked table
- 20-30 industries already produce visibly useful next moves

## Not Yet

- state overlays
- company drill-down
- accounts
- a full market-intelligence suite
