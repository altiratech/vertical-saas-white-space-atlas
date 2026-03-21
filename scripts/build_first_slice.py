#!/usr/bin/env python3

from __future__ import annotations

import argparse

from atlas_first_slice import build_first_slice


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch, normalize, score, and publish the first national NAICS slice."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-download of raw source artifacts before rebuilding outputs.",
    )
    args = parser.parse_args()

    payload = build_first_slice(refresh=args.refresh)
    summary = payload["summary"]
    print(
        "Built first slice with "
        f"{summary['fully_joined_rows']} fully joined industries and "
        f"{summary['excluded_rows']} excluded coverage-gap rows."
    )


if __name__ == "__main__":
    main()
