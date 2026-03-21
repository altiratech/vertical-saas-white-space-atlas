# Vertical SaaS White-Space Atlas Bootstrap Contract

Status: locked for scaffold-phase kickoff

## Toolchain Decision

- Slice 1 is Python-first using the shared fastlane environment at `/Users/ryanjameson/Desktop/Lifehub/.venv-fastlane`.
- Slice 1 does not require Node, a database, or deployment setup.
- The first explorer is static and file-backed.

## Start Rule

1. Start in `schemas/`, `scripts/`, `data/`, and `site/`.
2. Keep the first UI as plain static output.
3. Do not add JS build tooling until `site/data.json` exists and the ranked table already feels useful.

## First Executable Contract

Before any UI polish, produce:
- one schema for `industry_cell`
- one normalized CSV
- one scored JSON payload at `site/data.json`
- one minimal static explorer surface

## Explicit Defers

Do not start with:
- a web framework
- accounts
- a database
- deployment setup
