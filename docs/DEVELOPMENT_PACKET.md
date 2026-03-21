# Vertical SaaS White-Space Atlas Development Packet

Status: hydrated repo-local build packet

## Purpose

This file consolidates the original Karpathy1 implementation detail for this repo so it can be developed as a self-sufficient app without reopening the business-ideas folder for schema, source, scoring, or MVP guidance.

## Source Materials Absorbed

- `Business Ideas/01_Karpathy/Karpathy1/01_idea_audit.md`
- `Business Ideas/01_Karpathy/Karpathy1` evaluation outputs and implementation notes
- `Business Ideas/01_Karpathy/Karpathy1/03_top_candidates_mvp_specs.md`
- `Business Ideas/01_Karpathy/Karpathy1/04_top_pick_repo_plan.md`
- `Business Ideas/01_Karpathy/Karpathy1/05_assumption_risks.md`
- `Business Ideas/01_Karpathy/Karpathy1/data_source_catalog.md`
- `Business Ideas/01_Karpathy/KarpathyMerged/karpathy1_idea_lineage.md`
- `Business Ideas/01_Karpathy/KarpathyMerged/founder_context_and_selection_constraints.md`

## Product Thesis

Score NAICS industries for software wedge attractiveness using public business-demography and labor data.

More practically:
- turn public economic structure into a ranked answer to where to build
- where to sell
- where to acquire
- what to monitor
- what to ignore

## Why This Exists

- many vertical software or buy-and-build decisions still rely on anecdotes
- public data can make market selection more inspectable
- the product is most useful when it ends in a ranked move, not a generic market map

## First Users

Primary early users:
- founders
- acquisition entrepreneurs
- venture studios
- vertical SaaS operators
- strategy teams

## Job To Be Done

Which boring, fragmented markets are worth building into first?

## Canonical Object

Primary object:
- `industry_cell`

Granularity:
- 4-digit or 6-digit NAICS
- optional geography slice
- optional size band

## Strategic Role And Lineage

Original role:
- fast-to-build market-selection concept with clear public-data foundations

Current lineage note from the merged package:
- there is no exact one-to-one replacement
- the idea remains useful as both a venture-selection frame and a standalone app concept

Practical repo rule:
- this repo is still allowed to become its own app
- but it should preserve the sharper "ranked move engine" discipline from the later merged work

## Data Source Inventory

Primary v1 sources:
- Census County Business Patterns
- SBA size standards
- BLS employment or projection files

Useful additional sources:
- ZIP Code Business Patterns
- O*NET workflow enrichment

## Data Truth Rules

- use real public data or explicit placeholders only
- never fabricate industries, scores, or company examples
- keep raw source pulls, normalized tables, and AI-derived scores as separate layers
- every final ranked move should carry evidence, caveats, and confidence

## Canonical Schema

Core entity:
- `industry_cell`

Suggested v1 shape:

```json
{
  "entity_id": "naics:238220",
  "entity_name": "Plumbing, Heating, and Air-Conditioning Contractors",
  "entity_type": "naics_industry",
  "naics_code": "238220",
  "geography": {
    "level": "national",
    "code": "US",
    "name": "United States"
  },
  "size_band": "all",
  "anchors": {
    "establishments": 0,
    "employment": 0,
    "annual_payroll": 0,
    "avg_wage": 0
  },
  "scores": {
    "fragmentation": 0,
    "documentation_burden": 0,
    "compliance_intensity": 0,
    "workflow_complexity": 0,
    "willingness_to_pay": 0,
    "software_wedge": 0,
    "rollup_wedge": 0,
    "confidence": 0
  },
  "recommended_move": "incubate",
  "evidence": [],
  "caveats": [],
  "sources": [],
  "placeholder": false
}
```

## Scoring Model

Suggested scoring vector:
- documentation burden
- compliance intensity
- fragmentation
- scheduling complexity
- repetitive communication load
- willingness to pay
- AI wedge
- roll-up wedge
- confidence

Working rule:
- use deterministic scores first for fragmentation, size structure, and growth
- use LLM scoring only where inference is actually needed
- store component scores, not just one scalar

## Output Contract

Suggested top-level payload:

```json
{
  "generated_at": "2026-03-20",
  "method_version": "v1",
  "entities": [],
  "filters": {
    "geography_levels": ["national", "state", "county"],
    "size_bands": ["all", "small", "mid"],
    "views": ["software_wedge", "rollup_wedge", "underserved_niche"]
  }
}
```

## UI Guidance

Best UI shape:
- treemap for industry size
- ranked table for strongest wedge opportunities
- detail pane with evidence, scores, and caveats
- filters for geography, size band, wage level, and growth

Working rule:
- treemap is useful here, but the ranked table must still carry the decision weight

## MVP Build Sequence

Week 1:
- normalize CBP, SBA, and BLS
- produce first `industry_cells.csv`

Week 2:
- add inference scores
- generate `site/data.json`
- build the first static explorer

Week 3-4:
- refine the scoring rubric
- add evidence drawer and multiple views

Recommended coding sequence preserved from the source packet:
1. write schema files
2. build CBP and SBA fetchers
3. build one normalized table
4. add BLS overlay
5. create the scoring prompt and validator
6. generate `site/data.json`
7. build the static explorer

## Repo Shape

The current local repo shape already aligns well with the original plan:
- `raw/`
- `clean/`
- `data/`
- `site/`
- `prompts/`
- `schemas/`
- `scripts/`
- `docs/`
- `tests/`

This is the correct default shape for v1.

## Risks

Core risks:
- generic scoring language
- weak evidence linkage
- over-broad NAICS categories hiding the real wedge

Scoring risks:
- treating every fragmented market as equally attractive
- confusing operational mess with willingness to pay

Validation questions:
- 4-digit or 6-digit NAICS for v1
- national only or national plus state
- do 20-30 industries already produce visibly useful ranked moves

## Placeholder Rule

Allowed:
- empty `entities` arrays
- explicit source-status notes
- `placeholder: true`

Not allowed:
- invented NAICS rows
- invented scores
- fake industry evidence

## Practical Build Rule

Do not let this become:
- a broad company database
- an all-purpose TAM dashboard
- a generic AI market map

It has to remain a ranked move engine for founder decisions.
