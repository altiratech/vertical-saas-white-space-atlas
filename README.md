# Vertical SaaS White-Space Atlas

Vertical SaaS White-Space Atlas is a ranked market-selection engine for boring, fragmented industries.

It uses public business-demography, labor, and workflow data to identify software and roll-up wedges worth deeper investigation.

## Product Center

The founding loop is:
1. ingest public industry and labor anchors
2. normalize one inspectable industry table
3. score likely software and roll-up wedges
4. show evidence-backed ranked output

## Status

First real-data slice implemented.

Current slice:
- fetches official CBP, SBA, BLS, and Census crosswalk artifacts
- adds workflow signals from the BLS National Employment Matrix and O*NET work activities
- produces a normalized 6-digit national NAICS table in `clean/`
- writes scored industry cells in `data/`
- publishes a static explorer payload and plain HTML shortlist/compare plus memo-export surface in `site/`

## Quick Start

```bash
git clone https://github.com/altiratech/vertical-saas-white-space-atlas.git
cd vertical-saas-white-space-atlas
python3 scripts/build_first_slice.py
```

Outputs land in:
- `raw/` for cached source artifacts
- `clean/` for normalized tables
- `data/` for scored exports
- `site/data.json` for the static explorer payload
- `site/index.html` for the minimal explorer surface

## Canonical Build Truth

Treat these docs as authoritative:
- `docs/FOUNDING_PACKET.md`
- `docs/DEVELOPMENT_PACKET.md`
- `docs/BOOTSTRAP.md`
- `docs/FIRST_SLICE.md`
- `docs/IMPLEMENTATION_ENTRY_BRIEF.md`
- `docs/ARCHITECTURE_GUARDRAILS.md`

## Repo Shape

```text
raw/      cached public source pulls
clean/    normalized descriptions and lookup tables
data/     merged intermediate tables and scoring outputs
site/     static explorer
prompts/  scoring prompts and rubric contracts
schemas/  entity and score schemas
scripts/  fetch, normalize, score, and publish helpers
docs/     build truth and guardrails
tests/    schema, scoring, and pipeline coverage
```

## Build Rule

Do not drift into a broad market-intelligence platform before the ranked move engine works.

## License

No open-source license has been selected yet. Public source visibility does not grant reuse rights until a license file is added.
