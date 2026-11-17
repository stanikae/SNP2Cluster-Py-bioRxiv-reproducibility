#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def first_present(frame: pd.DataFrame, candidates: list[str], label: str) -> str:
    for column in candidates:
        if column in frame.columns:
            return column
    folded = {str(column).casefold(): column for column in frame.columns}
    for candidate in candidates:
        if candidate.casefold() in folded:
            return folded[candidate.casefold()]
    raise SystemExit(f"Could not resolve {label}. Available columns: {frame.columns.tolist()}")


def normalize(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def natural_key(value: object):
    text = normalize(value)
    return (0, int(text)) if text.isdigit() else (1, text.casefold())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank sequence types for Figure 4 by number of transmission clusters."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--min-clusters", type=int, default=2)
    parser.add_argument("--min-isolates", type=int, default=4)
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    table_path = args.run_dir / "tables" / "transmission_clusters.csv"
    if not table_path.exists():
        raise SystemExit(f"Missing table: {table_path}")

    frame = pd.read_csv(table_path, dtype=str)
    st_col = first_present(frame, ["ST", "st_type", "sequence_type"], "ST column")
    id_col = first_present(frame, ["sample_id", "sampleid", "sampleID", "SampleID", "name"], "isolate-ID column")
    cluster_col = first_present(frame, ["Clusters", "cluster", "transmission_cluster"], "cluster column")
    location_col = first_present(frame, ["FacilityCode", "facility_code", "Community", "community", "main_var"], "location column")

    frame[st_col] = frame[st_col].map(normalize)
    frame[cluster_col] = frame[cluster_col].map(normalize)
    excluded = {normalize(value) for value in args.exclude}

    rows = []
    for st, group in frame.groupby(st_col, dropna=False):
        st = normalize(st)
        if st in excluded:
            continue
        locations = sorted(group[location_col].dropna().astype(str).unique().tolist())
        clusters = sorted(group[cluster_col].dropna().astype(str).map(normalize).unique().tolist(), key=natural_key)
        rows.append({
            "ST": st,
            "clustered_isolates": group[id_col].nunique(),
            "transmission_clusters": len(clusters),
            "locations_count": len(locations),
            "clusters": ";".join(clusters),
            "locations": ";".join(locations),
            "scatterplot": str(args.run_dir / "figures" / f"02_transmission_scatter_ST_{st}.png"),
            "network_group": st,
        })

    result = pd.DataFrame(rows)
    result = result.loc[
        result["transmission_clusters"].ge(args.min_clusters)
        & result["clustered_isolates"].ge(args.min_isolates)
    ].copy()
    result = result.sort_values(
        ["transmission_clusters", "clustered_isolates", "locations_count", "ST"],
        ascending=[False, False, False, True],
    )

    output = args.output or (args.run_dir / "tables" / "figure4_candidate_STs.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)

    if result.empty:
        print("No ST met the requested criteria.")
    else:
        print(result.to_string(index=False))
    print(f"\nCandidate table: {output}")


if __name__ == "__main__":
    main()
