from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw"
CLEAN_DIR = ROOT / "clean"
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"

USER_AGENT = (
    "Mozilla/5.0 (compatible; VerticalSaaSWhiteSpaceAtlas/0.1; "
    "+https://local.vertical-saas-white-space-atlas)"
)

CBP_URL = (
    "https://api.census.gov/data/2022/cbp"
    "?get=NAICS2017,NAICS2017_LABEL,ESTAB,EMP,PAYANN&for=us:1&NAICS2017=*"
)
SBA_URL = (
    "https://www.sba.gov/sites/default/files/2023-06/"
    "Table%20of%20Size%20Standards_Effective%20March%2017%2C%202023_.xlsx"
)
BLS_URL = "https://data.bls.gov/cew/data/api/2024/a/area/US000.csv"
NAICS_CROSSWALK_URL = (
    "https://www.census.gov/naics/concordances/2022_to_2017_NAICS_Changes_Only.xlsx"
)

CBP_RAW_PATH = RAW_DIR / "cbp_2022_us_naics2017.json"
SBA_RAW_PATH = RAW_DIR / "sba_size_standards_2023.xlsx"
BLS_RAW_PATH = RAW_DIR / "bls_qcew_2024_us000_annual_area.csv"
NAICS_CROSSWALK_RAW_PATH = RAW_DIR / "naics_2022_to_2017_changes_only.xlsx"

CLEAN_CBP_2017_PATH = CLEAN_DIR / "cbp_2022_national_naics2017.csv"
CLEAN_CBP_2022_PATH = CLEAN_DIR / "cbp_2022_national_naics2022.csv"
CLEAN_BLS_PATH = CLEAN_DIR / "bls_qcew_2024_national_private_naics2022.csv"
CLEAN_SBA_PATH = CLEAN_DIR / "sba_size_standards_2023_naics2022.csv"
CLEAN_CROSSWALK_PATH = CLEAN_DIR / "naics_2022_to_2017_crosswalk.csv"
CLEAN_INDUSTRY_TABLE_PATH = CLEAN_DIR / "industry_table_national_naics2022.csv"

DATA_CELLS_JSON_PATH = DATA_DIR / "industry_cells.json"
DATA_CELLS_CSV_PATH = DATA_DIR / "industry_cells.csv"
DATA_COVERAGE_GAPS_PATH = DATA_DIR / "coverage_gaps.csv"
SITE_DATA_PATH = SITE_DIR / "data.json"

SOURCE_ARTIFACT_SCHEMA_PATH = ROOT / "schemas" / "source_artifact.schema.json"
SITE_PAYLOAD_SCHEMA_PATH = ROOT / "schemas" / "site_payload.schema.json"

NUMERIC_CODE_RE = re.compile(r"\d{6}")


@dataclass(frozen=True)
class SourceSpec:
    artifact_id: str
    name: str
    url: str
    local_path: Path
    vintage: str
    description: str


@dataclass(frozen=True)
class CBPRow2017:
    naics_code_2017: str
    naics_title_2017: str
    establishments: int
    employment: int
    annual_payroll_usd: int


@dataclass(frozen=True)
class BLSRow2022:
    naics_code_2022: str
    establishments: int
    employment: int
    average_annual_pay_usd: int
    employment_growth_pct: float
    pay_growth_pct: float
    disclosure_code: str


@dataclass(frozen=True)
class SBARow2022:
    naics_code_2022: str
    naics_title_2022: str
    size_standard_basis: str
    size_standard_value: float
    size_standard_display: str
    footnotes: list[str]


@dataclass(frozen=True)
class CrosswalkRow:
    naics_code_2022: str
    naics_title_2022: str
    status_code: str
    naics_codes_2017: list[str]
    naics_titles_2017: list[str]


SOURCE_SPECS = [
    SourceSpec(
        artifact_id="cbp_2022_us_national",
        name="Census County Business Patterns 2022 national industry API pull",
        url=CBP_URL,
        local_path=CBP_RAW_PATH,
        vintage="2022",
        description="National business-demography anchors from CBP, still keyed on NAICS 2017.",
    ),
    SourceSpec(
        artifact_id="sba_size_standards_2023",
        name="SBA Table of Size Standards effective March 17, 2023",
        url=SBA_URL,
        local_path=SBA_RAW_PATH,
        vintage="2023-03-17",
        description="Small-business size thresholds keyed on NAICS 2022.",
    ),
    SourceSpec(
        artifact_id="bls_qcew_2024_us000",
        name="BLS QCEW 2024 annual national area slice",
        url=BLS_URL,
        local_path=BLS_RAW_PATH,
        vintage="2024",
        description="Private-sector annual employment and pay anchors keyed on NAICS 2022.",
    ),
    SourceSpec(
        artifact_id="naics_2022_to_2017_changes_only",
        name="Census 2022 to 2017 NAICS changes workbook",
        url=NAICS_CROSSWALK_URL,
        local_path=NAICS_CROSSWALK_RAW_PATH,
        vintage="2022",
        description="Official changes-only bridge used to normalize CBP 2017 rows into 2022 industries.",
    ),
]


def build_first_slice(refresh: bool = False) -> dict[str, Any]:
    ensure_directories()

    fetched_sources = fetch_sources(refresh=refresh)
    cbp_2017 = load_cbp_rows(CBP_RAW_PATH)
    bls_2022 = load_bls_rows(BLS_RAW_PATH)
    sba_2022 = load_sba_rows(SBA_RAW_PATH)
    crosswalk_rows, new_to_old, old_to_new = load_crosswalk_rows(NAICS_CROSSWALK_RAW_PATH)
    all_candidate_codes = canonical_candidate_codes(cbp_2017, bls_2022, sba_2022, new_to_old, old_to_new)
    eligible_codes, base_coverage_gaps = split_eligible_codes(all_candidate_codes, bls_2022, sba_2022)

    write_csv(
        CLEAN_CROSSWALK_PATH,
        [
            {
                "naics_code_2022": row.naics_code_2022,
                "naics_title_2022": row.naics_title_2022,
                "status_code": row.status_code,
                "naics_codes_2017": "|".join(row.naics_codes_2017),
                "naics_titles_2017": "|".join(row.naics_titles_2017),
            }
            for row in crosswalk_rows
        ],
    )

    write_csv(
        CLEAN_CBP_2017_PATH,
        [
            {
                "naics_code_2017": row.naics_code_2017,
                "naics_title_2017": row.naics_title_2017,
                "establishments_2022": row.establishments,
                "employment_2022": row.employment,
                "annual_payroll_usd_2022": row.annual_payroll_usd,
                "average_annual_pay_usd_2022": safe_ratio(row.annual_payroll_usd, row.employment),
            }
            for row in cbp_2017.values()
        ],
    )

    cbp_2022_rows, cbp_coverage_gaps = normalize_cbp_to_2022(
        eligible_codes,
        cbp_2017,
        sba_2022,
        bls_2022,
        new_to_old,
        old_to_new,
    )
    coverage_gaps = merge_coverage_gaps(base_coverage_gaps, cbp_coverage_gaps)

    write_csv(
        CLEAN_CBP_2022_PATH,
        [
            {
                "naics_code_2022": row["naics_code_2022"],
                "naics_title_2022": row["naics_title_2022"],
                "cbp_mapping_type": row["cbp_mapping_type"],
                "cbp_source_naics_2017_codes": "|".join(row["cbp_source_naics_2017_codes"]),
                "cbp_establishments_2022": row["cbp_establishments_2022"],
                "cbp_employment_2022": row["cbp_employment_2022"],
                "cbp_annual_payroll_usd_2022": row["cbp_annual_payroll_usd_2022"],
                "cbp_average_annual_pay_usd_2022": row["cbp_average_annual_pay_usd_2022"],
            }
            for row in cbp_2022_rows.values()
        ],
    )

    write_csv(
        CLEAN_BLS_PATH,
        [
            {
                "naics_code_2022": row.naics_code_2022,
                "bls_establishments_2024": row.establishments,
                "bls_employment_2024": row.employment,
                "bls_average_annual_pay_usd_2024": row.average_annual_pay_usd,
                "bls_employment_growth_pct_2024": row.employment_growth_pct,
                "bls_pay_growth_pct_2024": row.pay_growth_pct,
                "bls_disclosure_code": row.disclosure_code,
            }
            for row in bls_2022.values()
        ],
    )

    write_csv(
        CLEAN_SBA_PATH,
        [
            {
                "naics_code_2022": row.naics_code_2022,
                "naics_title_2022": row.naics_title_2022,
                "size_standard_basis": row.size_standard_basis,
                "size_standard_value": row.size_standard_value,
                "size_standard_display": row.size_standard_display,
                "footnotes": "|".join(row.footnotes),
            }
            for row in sba_2022.values()
        ],
    )

    full_rows = assemble_full_rows(cbp_2022_rows, bls_2022, sba_2022, coverage_gaps)
    scored_rows = score_rows(full_rows)

    write_csv(
        CLEAN_INDUSTRY_TABLE_PATH,
        [
            flatten_for_csv(row)
            for row in scored_rows
        ],
    )
    write_csv(
        DATA_CELLS_CSV_PATH,
        [
            flatten_for_csv(row)
            for row in scored_rows
        ],
    )
    write_csv(
        DATA_COVERAGE_GAPS_PATH,
        coverage_gap_rows(coverage_gaps),
    )

    artifacts = [build_source_artifact(spec, fetched_sources[spec.artifact_id]) for spec in SOURCE_SPECS]
    payload = build_site_payload(scored_rows, coverage_gaps, artifacts)

    DATA_CELLS_JSON_PATH.write_text(json.dumps(scored_rows, indent=2) + "\n", encoding="utf-8")
    SITE_DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return payload


def ensure_directories() -> None:
    for directory in (RAW_DIR, CLEAN_DIR, DATA_DIR, SITE_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def fetch_sources(refresh: bool = False) -> dict[str, Path]:
    fetched: dict[str, Path] = {}
    for spec in SOURCE_SPECS:
        if refresh or not spec.local_path.exists():
            content = fetch_bytes(spec.url)
            spec.local_path.write_bytes(content)
        fetched[spec.artifact_id] = spec.local_path
    return fetched


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return response.read()


def load_cbp_rows(path: Path) -> dict[str, CBPRow2017]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    results: dict[str, CBPRow2017] = {}
    for naics_code, naics_title, establishments, employment, payann_k, *_ in rows[1:]:
        if not NUMERIC_CODE_RE.fullmatch(naics_code):
            continue
        annual_payroll_usd = int(payann_k) * 1_000
        results[naics_code] = CBPRow2017(
            naics_code_2017=naics_code,
            naics_title_2017=naics_title,
            establishments=int(establishments),
            employment=int(employment),
            annual_payroll_usd=annual_payroll_usd,
        )
    return results


def load_bls_rows(path: Path) -> dict[str, BLSRow2022]:
    rows: dict[str, BLSRow2022] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            code = raw["industry_code"].strip()
            if not NUMERIC_CODE_RE.fullmatch(code):
                continue
            if raw["own_code"] != "5" or raw["agglvl_code"] != "18":
                continue
            rows[code] = BLSRow2022(
                naics_code_2022=code,
                establishments=parse_int(raw["annual_avg_estabs"]),
                employment=parse_int(raw["annual_avg_emplvl"]),
                average_annual_pay_usd=parse_int(raw["avg_annual_pay"]),
                employment_growth_pct=parse_float(raw["oty_annual_avg_emplvl_pct_chg"]),
                pay_growth_pct=parse_float(raw["oty_avg_annual_pay_pct_chg"]),
                disclosure_code=raw["disclosure_code"].strip(),
            )
    return rows


def load_sba_rows(path: Path) -> dict[str, SBARow2022]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook["table_of_size_standards-all"]

    rows: dict[str, SBARow2022] = {}
    for raw in sheet.iter_rows(min_row=2, values_only=True):
        code_value = raw[0]
        if not isinstance(code_value, int):
            continue
        code = f"{code_value:06d}"
        if not NUMERIC_CODE_RE.fullmatch(code):
            continue

        title = clean_sba_title(raw[1] or "")
        receipts = raw[2]
        employees = raw[3]
        footnotes = parse_footnotes(raw[4])

        if isinstance(receipts, (int, float)):
            basis = "receipts_millions_usd"
            value = float(receipts)
            display = f"${value:,.2f}M"
        elif isinstance(receipts, str) and "assets" in receipts.lower():
            basis = "assets_millions_usd"
            value = parse_first_number(receipts)
            display = compact_whitespace(receipts)
        elif employees not in ("", None):
            basis = "employees"
            value = float(employees)
            display = f"{int(value):,} employees"
        else:
            continue

        rows[code] = SBARow2022(
            naics_code_2022=code,
            naics_title_2022=title,
            size_standard_basis=basis,
            size_standard_value=value,
            size_standard_display=display,
            footnotes=footnotes,
        )
    return rows


def load_crosswalk_rows(path: Path) -> tuple[list[CrosswalkRow], dict[str, list[str]], dict[str, list[str]]]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]

    rows: list[CrosswalkRow] = []
    new_to_old: dict[str, list[str]] = {}
    old_to_new: defaultdict[str, list[str]] = defaultdict(list)

    for raw in sheet.iter_rows(min_row=3, values_only=True):
        code_2022, title_2022, status_code, codes_2017_raw, titles_2017_raw, *_ = raw
        if code_2022 is None or codes_2017_raw is None:
            continue

        new_code = f"{int(code_2022):06d}"
        old_codes = [
            piece.strip().lstrip("*")
            for piece in str(codes_2017_raw).replace("\n", "|").split("|")
            if piece and piece.strip()
        ]
        old_titles = [
            compact_whitespace(piece)
            for piece in str(titles_2017_raw).split("\n")
            if piece and compact_whitespace(piece)
        ]

        row = CrosswalkRow(
            naics_code_2022=new_code,
            naics_title_2022=compact_whitespace(title_2022 or ""),
            status_code=str(status_code or "").strip(),
            naics_codes_2017=old_codes,
            naics_titles_2017=old_titles,
        )
        rows.append(row)
        new_to_old[new_code] = old_codes
        for old_code in old_codes:
            old_to_new[old_code].append(new_code)

    return rows, new_to_old, dict(old_to_new)


def normalize_cbp_to_2022(
    candidate_codes: list[str],
    cbp_2017: dict[str, CBPRow2017],
    sba_2022: dict[str, SBARow2022],
    bls_2022: dict[str, BLSRow2022],
    new_to_old: dict[str, list[str]],
    old_to_new: dict[str, list[str]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    coverage_gaps: dict[str, list[str]] = defaultdict(list)
    normalized: dict[str, dict[str, Any]] = {}

    for code in candidate_codes:
        supported = False
        source_codes: list[str] = []
        mapping_type = ""
        establishments = 0
        employment = 0
        annual_payroll_usd = 0

        if code in cbp_2017 and code not in old_to_new:
            supported = True
            mapping_type = "direct"
            source_codes = [code]
            source_row = cbp_2017[code]
            establishments = source_row.establishments
            employment = source_row.employment
            annual_payroll_usd = source_row.annual_payroll_usd
        elif code in new_to_old:
            source_codes = sorted(new_to_old[code])
            if not all(source_code in cbp_2017 for source_code in source_codes):
                coverage_gaps["missing_cbp_source_codes"].append(code)
                continue
            if any(len(old_to_new.get(source_code, [])) != 1 for source_code in source_codes):
                coverage_gaps["non_allocable_2017_split"].append(code)
                continue

            supported = True
            mapping_type = "aggregated_2017_to_2022"
            for source_code in source_codes:
                source_row = cbp_2017[source_code]
                establishments += source_row.establishments
                employment += source_row.employment
                annual_payroll_usd += source_row.annual_payroll_usd
        else:
            coverage_gaps["no_cbp_mapping"].append(code)
            continue

        if not supported:
            coverage_gaps["unsupported_cbp_mapping"].append(code)
            continue

        normalized[code] = {
            "naics_code_2022": code,
            "naics_title_2022": sba_2022[code].naics_title_2022,
            "cbp_mapping_type": mapping_type,
            "cbp_source_naics_2017_codes": source_codes,
            "cbp_establishments_2022": establishments,
            "cbp_employment_2022": employment,
            "cbp_annual_payroll_usd_2022": annual_payroll_usd,
            "cbp_average_annual_pay_usd_2022": round(safe_ratio(annual_payroll_usd, employment), 2),
        }

    for reason in sorted(coverage_gaps):
        coverage_gaps[reason] = sorted(set(coverage_gaps[reason]))

    return normalized, dict(coverage_gaps)


def assemble_full_rows(
    cbp_2022_rows: dict[str, dict[str, Any]],
    bls_2022: dict[str, BLSRow2022],
    sba_2022: dict[str, SBARow2022],
    coverage_gaps: dict[str, list[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code in sorted(set(cbp_2022_rows) & set(bls_2022) & set(sba_2022)):
        cbp_row = cbp_2022_rows[code]
        bls_row = bls_2022[code]
        sba_row = sba_2022[code]

        employees_per_establishment = safe_ratio(
            cbp_row["cbp_employment_2022"],
            cbp_row["cbp_establishments_2022"],
        )
        payroll_per_establishment = safe_ratio(
            cbp_row["cbp_annual_payroll_usd_2022"],
            cbp_row["cbp_establishments_2022"],
        )
        employment_gap_ratio = safe_ratio(bls_row.employment, cbp_row["cbp_employment_2022"])

        caveats = [
            "National-only slice; regional density and local regulatory variation are not yet represented.",
            "Workflow burden is inferred from public industry structure, not company-level software workflow evidence.",
        ]
        if cbp_row["cbp_mapping_type"] == "aggregated_2017_to_2022":
            caveats.append(
                "CBP business anchors are aggregated forward from 2017 NAICS into the 2022 definition."
            )
        if employment_gap_ratio < 0.7 or employment_gap_ratio > 1.3:
            caveats.append(
                "CBP 2022 employment and BLS 2024 private-sector employment differ materially; treat labor scale as directional."
            )

        row = {
            "entity_id": f"naics:{code}",
            "entity_name": sba_row.naics_title_2022,
            "entity_type": "naics_industry",
            "naics_code": code,
            "naics_version": "2022",
            "geography": {
                "level": "national",
                "code": "US",
                "name": "United States",
            },
            "size_band": "all",
            "placeholder": False,
            "lineage": {
                "cbp_mapping_type": cbp_row["cbp_mapping_type"],
                "cbp_source_naics_2017_codes": cbp_row["cbp_source_naics_2017_codes"],
                "source_vintages": {
                    "cbp": "2022",
                    "sba": "2023-03-17",
                    "bls": "2024",
                },
            },
            "anchors": {
                "cbp_establishments": cbp_row["cbp_establishments_2022"],
                "cbp_employment": cbp_row["cbp_employment_2022"],
                "cbp_annual_payroll_usd": cbp_row["cbp_annual_payroll_usd_2022"],
                "cbp_average_annual_pay_usd": cbp_row["cbp_average_annual_pay_usd_2022"],
                "bls_establishments": bls_row.establishments,
                "bls_employment": bls_row.employment,
                "bls_average_annual_pay_usd": bls_row.average_annual_pay_usd,
                "bls_employment_growth_pct": bls_row.employment_growth_pct,
                "bls_pay_growth_pct": bls_row.pay_growth_pct,
                "sba_size_standard": {
                    "basis": sba_row.size_standard_basis,
                    "value": sba_row.size_standard_value,
                    "display": sba_row.size_standard_display,
                    "footnotes": sba_row.footnotes,
                },
            },
            "score_inputs": {
                "employees_per_establishment": round(employees_per_establishment, 2),
                "payroll_per_establishment_usd": round(payroll_per_establishment, 2),
                "employment_gap_ratio_bls_to_cbp": round(employment_gap_ratio, 3),
                "sba_size_standard_basis": sba_row.size_standard_basis,
                "sba_size_standard_value": sba_row.size_standard_value,
            },
            "scores": {},
            "recommended_move": "",
            "summary": "",
            "evidence": [],
            "caveats": caveats,
            "sources": [
                "cbp_2022_us_national",
                "sba_size_standards_2023",
                "bls_qcew_2024_us000",
                "naics_2022_to_2017_changes_only",
            ],
        }
        rows.append(row)

    if coverage_gaps:
        rows.sort(key=lambda item: item["naics_code"])
    return rows


def score_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows

    estab_logs = [math.log10(row["anchors"]["cbp_establishments"] + 1) for row in rows]
    emp_per_estab_logs = [
        math.log10(row["score_inputs"]["employees_per_establishment"] + 1) for row in rows
    ]
    payroll_per_estab_logs = [
        math.log10(row["score_inputs"]["payroll_per_establishment_usd"] + 1) for row in rows
    ]
    pay_logs = [math.log10(row["anchors"]["bls_average_annual_pay_usd"] + 1) for row in rows]
    growth_values = [row["anchors"]["bls_employment_growth_pct"] for row in rows]
    pay_growth_values = [row["anchors"]["bls_pay_growth_pct"] for row in rows]
    employment_logs = [math.log10(row["anchors"]["cbp_employment"] + 1) for row in rows]
    payroll_logs = [math.log10(row["anchors"]["cbp_annual_payroll_usd"] + 1) for row in rows]

    dollar_threshold_logs = [
        math.log10(
            row["anchors"]["sba_size_standard"]["value"] * 1_000_000 + 1
        )
        for row in rows
        if row["anchors"]["sba_size_standard"]["basis"] in {"receipts_millions_usd", "assets_millions_usd"}
    ]
    employee_threshold_logs = [
        math.log10(row["anchors"]["sba_size_standard"]["value"] + 1)
        for row in rows
        if row["anchors"]["sba_size_standard"]["basis"] == "employees"
    ]

    for row in rows:
        estab_pct = percentile(estab_logs, math.log10(row["anchors"]["cbp_establishments"] + 1))
        small_firm_pct = inverse_percentile(
            emp_per_estab_logs,
            math.log10(row["score_inputs"]["employees_per_establishment"] + 1),
        )
        employees_per_estab_pct = percentile(
            emp_per_estab_logs,
            math.log10(row["score_inputs"]["employees_per_establishment"] + 1),
        )
        payroll_per_estab_pct = percentile(
            payroll_per_estab_logs,
            math.log10(row["score_inputs"]["payroll_per_establishment_usd"] + 1),
        )
        pay_pct = percentile(
            pay_logs,
            math.log10(row["anchors"]["bls_average_annual_pay_usd"] + 1),
        )
        growth_pct = percentile(growth_values, row["anchors"]["bls_employment_growth_pct"])
        pay_growth_pct = percentile(pay_growth_values, row["anchors"]["bls_pay_growth_pct"])
        employment_pct = percentile(
            employment_logs,
            math.log10(row["anchors"]["cbp_employment"] + 1),
        )
        payroll_pct = percentile(
            payroll_logs,
            math.log10(row["anchors"]["cbp_annual_payroll_usd"] + 1),
        )

        sba_basis = row["anchors"]["sba_size_standard"]["basis"]
        if sba_basis in {"receipts_millions_usd", "assets_millions_usd"}:
            sba_pct = percentile(
                dollar_threshold_logs,
                math.log10(row["anchors"]["sba_size_standard"]["value"] * 1_000_000 + 1),
            )
        else:
            sba_pct = percentile(
                employee_threshold_logs,
                math.log10(row["anchors"]["sba_size_standard"]["value"] + 1),
            )

        fragmentation = weighted_average(
            [(0.55, estab_pct), (0.45, small_firm_pct)]
        )
        inverse_pay_pct = inverse_percentile(
            pay_logs,
            math.log10(row["anchors"]["bls_average_annual_pay_usd"] + 1),
        )
        operating_complexity = weighted_average(
            [(0.7, employees_per_estab_pct), (0.3, inverse_pay_pct)]
        )
        willingness_to_pay = weighted_average(
            [(0.55, sba_pct), (0.45, payroll_per_estab_pct)]
        )
        growth = weighted_average(
            [(0.7, growth_pct), (0.3, pay_growth_pct)]
        )
        market_scale = weighted_average(
            [(0.5, employment_pct), (0.5, payroll_pct)]
        )

        software_wedge = weighted_average(
            [
                (0.35, fragmentation),
                (0.3, operating_complexity),
                (0.15, willingness_to_pay),
                (0.1, growth),
                (0.1, market_scale),
            ]
        )
        rollup_wedge = weighted_average(
            [
                (0.45, fragmentation),
                (0.2, market_scale),
                (0.2, sba_pct),
                (0.1, operating_complexity),
                (0.05, growth),
            ]
        )

        confidence = 90.0
        if row["lineage"]["cbp_mapping_type"] == "aggregated_2017_to_2022":
            confidence -= 10.0
        employment_gap_ratio = row["score_inputs"]["employment_gap_ratio_bls_to_cbp"]
        if employment_gap_ratio < 0.7 or employment_gap_ratio > 1.3:
            confidence -= 5.0

        row["scores"] = {
            "fragmentation": round(fragmentation, 1),
            "operating_complexity": round(operating_complexity, 1),
            "willingness_to_pay": round(willingness_to_pay, 1),
            "growth": round(growth, 1),
            "market_scale": round(market_scale, 1),
            "software_wedge": round(software_wedge, 1),
            "rollup_wedge": round(rollup_wedge, 1),
            "confidence": round(max(confidence, 55.0), 1),
        }
        row["recommended_move"] = recommend_move(row["scores"])
        row["summary"] = build_summary(row)
        row["evidence"] = build_evidence(row)

    rows.sort(
        key=lambda item: (
            move_priority(item["recommended_move"]),
            -primary_rank_score(item),
            -item["scores"]["software_wedge"],
            -item["scores"]["rollup_wedge"],
            item["entity_name"],
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    return rows


def build_site_payload(
    scored_rows: list[dict[str, Any]],
    coverage_gaps: dict[str, list[str]],
    source_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    move_counts = Counter(row["recommended_move"] for row in scored_rows)
    score_values = [row["scores"]["software_wedge"] for row in scored_rows]
    rollup_values = [row["scores"]["rollup_wedge"] for row in scored_rows]
    confidence_values = [row["scores"]["confidence"] for row in scored_rows]

    excluded_total = sum(len(values) for values in coverage_gaps.values())
    return {
        "generated_at": iso_timestamp(),
        "method_version": "first-slice-v1",
        "canonical_naics_version": "2022",
        "summary": {
            "fully_joined_rows": len(scored_rows),
            "excluded_rows": excluded_total,
            "excluded_by_reason": {
                reason: len(values)
                for reason, values in sorted(coverage_gaps.items())
            },
            "recommended_move_counts": dict(sorted(move_counts.items())),
            "software_wedge_range": [min(score_values), max(score_values)],
            "rollup_wedge_range": [min(rollup_values), max(rollup_values)],
            "confidence_range": [min(confidence_values), max(confidence_values)],
            "national_only": True,
        },
        "coverage_gaps": {
            reason: {
                "count": len(values),
                "sample_codes": values[:15],
            }
            for reason, values in sorted(coverage_gaps.items())
        },
        "source_artifacts": source_artifacts,
        "filters": {
            "recommended_moves": sorted(move_counts),
            "score_fields": [
                "software_wedge",
                "rollup_wedge",
                "fragmentation",
                "operating_complexity",
                "willingness_to_pay",
                "growth",
                "market_scale",
                "confidence",
            ],
        },
        "entities": scored_rows,
    }


def build_source_artifact(spec: SourceSpec, local_path: Path) -> dict[str, Any]:
    content = local_path.read_bytes()
    return {
        "artifact_id": spec.artifact_id,
        "name": spec.name,
        "url": spec.url,
        "local_path": str(local_path.relative_to(ROOT)),
        "vintage": spec.vintage,
        "description": spec.description,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


def build_evidence(row: dict[str, Any]) -> list[dict[str, Any]]:
    anchors = row["anchors"]
    score_inputs = row["score_inputs"]
    evidence = [
        {
            "label": "CBP footprint",
            "detail": (
                f"{anchors['cbp_establishments']:,} establishments and "
                f"{anchors['cbp_employment']:,} employees in 2022."
            ),
            "source_ids": ["cbp_2022_us_national"],
        },
        {
            "label": "BLS labor pricing",
            "detail": (
                f"Private-sector average annual pay was "
                f"${anchors['bls_average_annual_pay_usd']:,.0f} in 2024."
            ),
            "source_ids": ["bls_qcew_2024_us000"],
        },
        {
            "label": "BLS momentum",
            "detail": (
                f"Employment changed {anchors['bls_employment_growth_pct']:+.1f}% "
                f"and pay changed {anchors['bls_pay_growth_pct']:+.1f}% year over year."
            ),
            "source_ids": ["bls_qcew_2024_us000"],
        },
        {
            "label": "Operator density",
            "detail": (
                f"Average establishment size is "
                f"{score_inputs['employees_per_establishment']:,.1f} employees."
            ),
            "source_ids": ["cbp_2022_us_national"],
        },
        {
            "label": "SBA buyer boundary",
            "detail": (
                f"SBA small-business threshold is "
                f"{anchors['sba_size_standard']['display']}."
            ),
            "source_ids": ["sba_size_standards_2023"],
        },
    ]
    if row["lineage"]["cbp_mapping_type"] == "aggregated_2017_to_2022":
        evidence.append(
            {
                "label": "Crosswalk note",
                "detail": (
                    "CBP anchors aggregate the 2017 NAICS source codes "
                    + ", ".join(row["lineage"]["cbp_source_naics_2017_codes"])
                    + " into this 2022 definition."
                ),
                "source_ids": [
                    "cbp_2022_us_national",
                    "naics_2022_to_2017_changes_only",
                ],
            }
        )
    return evidence


def build_summary(row: dict[str, Any]) -> str:
    move = row["recommended_move"]
    scores = row["scores"]
    if move == "build":
        return (
            "High fragmentation, meaningful operating complexity, and credible pay power "
            "make this a build-first software target."
        )
    if move == "acquire":
        return (
            "The market looks more compelling as a fragmented roll-up lane than as a pure "
            "software wedge."
        )
    if move == "sell":
        return (
            "The structure supports go-to-market attention now, but the software wedge still "
            "looks less decisive than the very top build candidates."
        )
    if move == "monitor":
        if scores["growth"] >= scores["willingness_to_pay"]:
            return "Momentum is present, but the buyer-quality signals are still mixed."
        return "There is some structural promise here, but the current evidence is not strong enough for a first move."
    return "The current public-data signals look too weak for a near-term build, sell, or acquire motion."


def recommend_move(scores: dict[str, float]) -> str:
    if (
        scores["software_wedge"] >= 60
        and scores["fragmentation"] >= 65
        and scores["operating_complexity"] >= 40
        and scores["willingness_to_pay"] >= 35
    ):
        return "build"
    if scores["rollup_wedge"] >= 70 and scores["fragmentation"] >= 75:
        return "acquire"
    if scores["software_wedge"] >= 58 or scores["rollup_wedge"] >= 60:
        return "sell"
    if scores["software_wedge"] >= 45 or scores["growth"] >= 55:
        return "monitor"
    return "ignore"


def coverage_gap_rows(coverage_gaps: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for reason, codes in sorted(coverage_gaps.items()):
        for code in codes:
            rows.append(
                {
                    "naics_code_2022": code,
                    "reason": reason,
                }
            )
    return rows


def flatten_for_csv(row: dict[str, Any]) -> dict[str, Any]:
    anchors = row["anchors"]
    sba_size = anchors["sba_size_standard"]
    return {
        "rank": row["rank"],
        "naics_code": row["naics_code"],
        "entity_name": row["entity_name"],
        "cbp_mapping_type": row["lineage"]["cbp_mapping_type"],
        "cbp_source_naics_2017_codes": "|".join(row["lineage"]["cbp_source_naics_2017_codes"]),
        "cbp_establishments_2022": anchors["cbp_establishments"],
        "cbp_employment_2022": anchors["cbp_employment"],
        "cbp_annual_payroll_usd_2022": anchors["cbp_annual_payroll_usd"],
        "cbp_average_annual_pay_usd_2022": anchors["cbp_average_annual_pay_usd"],
        "bls_establishments_2024": anchors["bls_establishments"],
        "bls_employment_2024": anchors["bls_employment"],
        "bls_average_annual_pay_usd_2024": anchors["bls_average_annual_pay_usd"],
        "bls_employment_growth_pct_2024": anchors["bls_employment_growth_pct"],
        "bls_pay_growth_pct_2024": anchors["bls_pay_growth_pct"],
        "sba_size_standard_basis": sba_size["basis"],
        "sba_size_standard_value": sba_size["value"],
        "sba_size_standard_display": sba_size["display"],
        "employees_per_establishment": row["score_inputs"]["employees_per_establishment"],
        "payroll_per_establishment_usd": row["score_inputs"]["payroll_per_establishment_usd"],
        "employment_gap_ratio_bls_to_cbp": row["score_inputs"]["employment_gap_ratio_bls_to_cbp"],
        "fragmentation": row["scores"]["fragmentation"],
        "operating_complexity": row["scores"]["operating_complexity"],
        "willingness_to_pay": row["scores"]["willingness_to_pay"],
        "growth": row["scores"]["growth"],
        "market_scale": row["scores"]["market_scale"],
        "software_wedge": row["scores"]["software_wedge"],
        "rollup_wedge": row["scores"]["rollup_wedge"],
        "confidence": row["scores"]["confidence"],
        "recommended_move": row["recommended_move"],
        "summary": row["summary"],
        "caveats": " | ".join(row["caveats"]),
    }


def parse_int(value: str) -> int:
    if value in ("", None):
        return 0
    return int(float(value))


def parse_float(value: str) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def parse_footnotes(value: Any) -> list[str]:
    if value in ("", None):
        return []
    return [compact_whitespace(piece) for piece in str(value).split(",") if compact_whitespace(piece)]


def percentile(values: list[float], value: float) -> float:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return 50.0
    lower = sum(1 for item in ordered if item < value)
    equal = sum(1 for item in ordered if item == value)
    return round(((lower + (equal / 2)) / count) * 100, 1)


def inverse_percentile(values: list[float], value: float) -> float:
    return round(100.0 - percentile(values, value), 1)


def weighted_average(weighted_values: list[tuple[float, float]]) -> float:
    numerator = sum(weight * value for weight, value in weighted_values)
    denominator = sum(weight for weight, _ in weighted_values)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def safe_ratio(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator


def compact_whitespace(value: str) -> str:
    return " ".join(str(value).split())


def canonical_candidate_codes(
    cbp_2017: dict[str, CBPRow2017],
    bls_2022: dict[str, BLSRow2022],
    sba_2022: dict[str, SBARow2022],
    new_to_old: dict[str, list[str]],
    old_to_new: dict[str, list[str]],
) -> list[str]:
    unchanged_cbp_codes = {code for code in cbp_2017 if code not in old_to_new}
    return sorted(set(bls_2022) | set(sba_2022) | set(new_to_old) | unchanged_cbp_codes)


def split_eligible_codes(
    all_candidate_codes: list[str],
    bls_2022: dict[str, BLSRow2022],
    sba_2022: dict[str, SBARow2022],
) -> tuple[list[str], dict[str, list[str]]]:
    eligible: list[str] = []
    coverage_gaps: dict[str, list[str]] = defaultdict(list)

    for code in all_candidate_codes:
        has_bls = code in bls_2022
        has_sba = code in sba_2022
        if has_bls and has_sba:
            eligible.append(code)
        elif has_bls and not has_sba:
            coverage_gaps["missing_sba_row"].append(code)
        elif has_sba and not has_bls:
            coverage_gaps["missing_bls_row"].append(code)
        else:
            coverage_gaps["missing_bls_and_sba_row"].append(code)

    return eligible, dict(coverage_gaps)


def merge_coverage_gaps(*gap_sets: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for gap_set in gap_sets:
        for reason, codes in gap_set.items():
            merged[reason].update(codes)
    return {reason: sorted(codes) for reason, codes in sorted(merged.items())}


def move_priority(move: str) -> int:
    return {
        "build": 0,
        "acquire": 1,
        "sell": 2,
        "monitor": 3,
        "ignore": 4,
    }[move]


def primary_rank_score(row: dict[str, Any]) -> float:
    if row["recommended_move"] == "build":
        return row["scores"]["software_wedge"]
    if row["recommended_move"] == "acquire":
        return row["scores"]["rollup_wedge"]
    return max(row["scores"]["software_wedge"], row["scores"]["rollup_wedge"])


def clean_sba_title(value: str) -> str:
    return re.sub(r"(?<=\D)\d+$", "", compact_whitespace(value)).strip()


def parse_first_number(value: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    if not match:
        raise ValueError(f"Could not parse numeric value from {value!r}")
    return float(match.group(1))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
