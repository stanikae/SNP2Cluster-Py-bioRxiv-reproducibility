#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from configured_columns import (
    load_configured_columns,
    resolve_sample_id_column,
    resolve_st_column,
    resolve_table_column,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize manuscript analysis results using "
            "the dataset variables defined in the YAML configuration."
        )
    )

    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--groups",
        nargs="*",
        default=[],
        help=(
            "Optional ST or main-variable values to summarize, "
            "for example 802 5541."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    schema = load_configured_columns(
        args.config
    )

    core = pd.read_csv(
        args.run_dir
        / "tables"
        / "core_snp_clusters.csv",
        dtype=str,
    )

    transmission = pd.read_csv(
        args.run_dir
        / "tables"
        / "transmission_clusters.csv",
        dtype=str,
    )

    core_id = resolve_sample_id_column(
        core,
        schema.sample_id,
    )

    transmission_id = resolve_sample_id_column(
        transmission,
        schema.sample_id,
    )

    core_st = resolve_st_column(
        core,
        schema.st_var,
    )

    transmission_st = resolve_st_column(
        transmission,
        schema.st_var,
    )

    location = resolve_table_column(
        transmission,
        schema.secondary_var,
        aliases=[
            "FacilityCode",
            "facility_code",
            "ward_type",
            "Community",
        ],
        label="the configured secondary variable",
    )

    cluster = resolve_table_column(
        transmission,
        "Clusters",
        aliases=[
            "cluster",
            "transmission_cluster",
        ],
        label="the transmission-cluster column",
    )

    print("CONFIGURATION")
    print("-------------")
    print("Config:", args.config)
    print("Run:", args.run_dir)
    print("Main variable:", schema.main_var)
    print(
        "Secondary variable:",
        schema.secondary_var,
    )
    print("Date variable:", schema.date_var)
    print("Date format:", schema.date_format)
    print(
        "Core context:",
        list(schema.core_context),
    )
    print("Cluster type:", schema.cluster_type)
    print(
        "Transmission level:",
        schema.transmission_level,
    )
    print("SNP cutoff:", schema.snp_cutoff)
    print("Days cutoff:", schema.days_cutoff)

    print("\nRESOLVED OUTPUT COLUMNS")
    print("-----------------------")
    print("Core isolate ID:", core_id)
    print(
        "Transmission isolate ID:",
        transmission_id,
    )
    print("Core ST:", core_st)
    print("Transmission ST:", transmission_st)
    print("Location:", location)
    print("Cluster:", cluster)

    groups = args.groups

    if not groups:
        groups = sorted(
            transmission[
                transmission_st
            ]
            .dropna()
            .map(normalize_value)
            .unique()
            .tolist()
        )

    for group in groups:
        normalized_group = normalize_value(
            group
        )

        core_subset = core.loc[
            core[core_st]
            .fillna("")
            .map(normalize_value)
            .eq(normalized_group)
        ].copy()

        transmission_subset = transmission.loc[
            transmission[
                transmission_st
            ]
            .fillna("")
            .map(normalize_value)
            .eq(normalized_group)
        ].copy()

        print("\n" + "=" * 72)
        print(f"ST{normalized_group}")
        print("=" * 72)

        print(
            "Core-clustered isolates:",
            core_subset[core_id].nunique(),
        )

        print(
            "Transmission-clustered isolates:",
            transmission_subset[
                transmission_id
            ].nunique(),
        )

        print(
            "Transmission clusters:",
            transmission_subset[
                cluster
            ].nunique(),
        )

        locations = sorted(
            transmission_subset[
                location
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        print("Locations:", locations)

        selected = []

        for column in [
            transmission_id,
            transmission_st,
            cluster,
            "Cluster_Cases_count",
            location,
            "_core_context",
            "core_cluster_label",
        ]:
            if (
                column in transmission_subset.columns
                and column not in selected
            ):
                selected.append(column)

        if transmission_subset.empty:
            print("No clustered isolates found.")
            continue

        sort_columns = [
            column
            for column in [
                cluster,
                location,
                transmission_id,
            ]
            if column in selected
        ]

        print("\nMembership:")
        print(
            transmission_subset[selected]
            .sort_values(sort_columns)
            .to_string(index=False)
        )


def normalize_value(
    value: object,
) -> str:
    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text


if __name__ == "__main__":
    main()
