from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atlas_first_slice  # noqa: E402


def test_build_outputs_and_schema() -> None:
    payload = atlas_first_slice.build_first_slice(refresh=False)

    assert payload["summary"]["fully_joined_rows"] >= 800
    assert payload["summary"]["national_only"] is True
    assert payload["summary"]["excluded_rows"] >= 1

    schema = json.loads((ROOT / "schemas" / "site_payload.schema.json").read_text(encoding="utf-8"))
    rendered_payload = json.loads((ROOT / "site" / "data.json").read_text(encoding="utf-8"))
    jsonschema.validate(rendered_payload, schema)


def test_crosswalk_aggregates_known_consolidation() -> None:
    atlas_first_slice.build_first_slice(refresh=False)

    cbp_2017 = atlas_first_slice.load_cbp_rows(ROOT / "raw" / "cbp_2022_us_naics2017.json")
    sba_2022 = atlas_first_slice.load_sba_rows(ROOT / "raw" / "sba_size_standards_2023.xlsx")
    bls_2022 = atlas_first_slice.load_bls_rows(ROOT / "raw" / "bls_qcew_2024_us000_annual_area.csv")
    _, new_to_old, old_to_new = atlas_first_slice.load_crosswalk_rows(
        ROOT / "raw" / "naics_2022_to_2017_changes_only.xlsx"
    )
    candidate_codes = atlas_first_slice.canonical_candidate_codes(
        cbp_2017,
        bls_2022,
        sba_2022,
        new_to_old,
        old_to_new,
    )
    eligible_codes, _ = atlas_first_slice.split_eligible_codes(candidate_codes, bls_2022, sba_2022)
    cbp_2022_rows, _ = atlas_first_slice.normalize_cbp_to_2022(
        eligible_codes,
        cbp_2017,
        sba_2022,
        bls_2022,
        new_to_old,
        old_to_new,
    )

    aggregated = cbp_2022_rows["212220"]
    assert aggregated["cbp_mapping_type"] == "aggregated_2017_to_2022"
    assert aggregated["cbp_source_naics_2017_codes"] == ["212221", "212222"]
    assert aggregated["cbp_establishments_2022"] == (
        cbp_2017["212221"].establishments + cbp_2017["212222"].establishments
    )


def test_rankings_are_sorted_and_evidence_backed() -> None:
    payload = atlas_first_slice.build_first_slice(refresh=False)
    rows = payload["entities"]

    assert rows == sorted(
        rows,
        key=lambda item: (
            atlas_first_slice.move_priority(item["recommended_move"]),
            -atlas_first_slice.primary_rank_score(item),
            -item["scores"]["software_wedge"],
            -item["scores"]["rollup_wedge"],
            item["entity_name"],
        ),
    )

    top_ten = rows[:10]
    assert all(row["evidence"] for row in top_ten)
    assert all(row["caveats"] for row in top_ten)
    assert all(row["recommended_move"] in {"build", "sell", "acquire", "monitor", "ignore"} for row in top_ten)
    assert all("thesis_fit" in row["scores"] for row in top_ten)


def test_ranking_quality_prefers_operator_markets_over_native_software_and_finance() -> None:
    payload = atlas_first_slice.build_first_slice(refresh=False)
    lookup = {row["naics_code"]: row for row in payload["entities"]}

    assert lookup["722310"]["recommended_move"] == "build"
    assert lookup["513210"]["recommended_move"] != "build"
    assert lookup["523940"]["recommended_move"] != "build"
    assert lookup["722310"]["rank"] < lookup["513210"]["rank"]
    assert lookup["621610"]["rank"] < lookup["524114"]["rank"]
    assert lookup["722310"]["scores"]["thesis_fit"] > lookup["513210"]["scores"]["thesis_fit"]


def test_site_and_data_outputs_exist() -> None:
    atlas_first_slice.build_first_slice(refresh=False)

    for path in [
        ROOT / "clean" / "industry_table_national_naics2022.csv",
        ROOT / "data" / "industry_cells.json",
        ROOT / "data" / "coverage_gaps.csv",
        ROOT / "site" / "data.json",
    ]:
        assert path.exists()
        assert path.stat().st_size > 0
