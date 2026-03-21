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

This repo is a fresh scaffold.

The current goal is to establish:
- founding docs
- implementation guardrails
- a stable repo shape

before major code expands.

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
