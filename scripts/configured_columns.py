#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml


@dataclass(frozen=True)
class ConfiguredColumns:
    sample_id: str | None
    main_var: str
    secondary_var: str
    date_var: str
    st_var: str | None
    date_format: str
    core_context: tuple[str, ...]
    cluster_type: str
    transmission_level: str
    snp_cutoff: float | None
    days_cutoff: float | None


def _mapping(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _first_config_value(
    mappings: Iterable[dict],
    candidates: Iterable[str],
) -> object | None:
    candidate_keys = {
        candidate.casefold()
        for candidate in candidates
    }

    for mapping in mappings:
        for key, value in mapping.items():
            if str(key).casefold() in candidate_keys:
                if value not in (None, ""):
                    return value

    return None


def load_configured_columns(
    config_path: Path,
) -> ConfiguredColumns:
    with config_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        config = yaml.safe_load(handle) or {}

    variables = _mapping(
        config.get("variables")
    )

    analysis = _mapping(
        config.get("analysis")
    )

    columns = _mapping(
        config.get("columns")
    )

    input_config = _mapping(
        config.get("input")
    )

    mappings = [
        variables,
        columns,
        input_config,
        config,
    ]

    main_var = _first_config_value(
        mappings,
        [
            "main_var",
            "main_variable",
        ],
    )

    secondary_var = _first_config_value(
        mappings,
        [
            "var_01",
            "secondary_var",
            "secondary_variable",
        ],
    )

    date_var = _first_config_value(
        mappings,
        [
            "var_02",
            "date_var",
            "date_column",
            "collection_date_column",
        ],
    )

    sample_id = _first_config_value(
        mappings,
        [
            "sample_id",
            "sample_id_column",
            "sampleid",
            "sample_column",
            "id_column",
        ],
    )

    st_var = _first_config_value(
        mappings,
        [
            "st",
            "st_column",
            "sequence_type",
            "sequence_type_column",
            "mlst",
            "mlst_column",
        ],
    )

    if main_var is None:
        raise ValueError(
            "The YAML configuration does not define "
            "variables.main_var."
        )

    if secondary_var is None:
        raise ValueError(
            "The YAML configuration does not define "
            "variables.var_01."
        )

    if date_var is None:
        raise ValueError(
            "The YAML configuration does not define "
            "variables.var_02."
        )

    context = analysis.get(
        "core_cluster_context",
        [],
    )

    if isinstance(context, str):
        context = [context]

    return ConfiguredColumns(
        sample_id=(
            str(sample_id)
            if sample_id is not None
            else None
        ),
        main_var=str(main_var),
        secondary_var=str(secondary_var),
        date_var=str(date_var),
        st_var=(
            str(st_var)
            if st_var is not None
            else None
        ),
        date_format=str(
            analysis.get(
                "date_format",
                config.get(
                    "date_format",
                    "ymd",
                ),
            )
        ),
        core_context=tuple(
            str(value)
            for value in context
        ),
        cluster_type=str(
            analysis.get(
                "cluster_type",
                "",
            )
        ),
        transmission_level=str(
            analysis.get(
                "transmission_level",
                "",
            )
        ),
        snp_cutoff=_optional_float(
            analysis.get("snp_cutoff")
        ),
        days_cutoff=_optional_float(
            analysis.get("days_cutoff")
        ),
    )


def _optional_float(
    value: object,
) -> float | None:
    if value in (None, ""):
        return None

    return float(value)


def resolve_table_column(
    frame: pd.DataFrame,
    configured_name: str | None,
    *,
    aliases: Iterable[str] = (),
    label: str,
) -> str:
    """Resolve a configured variable against one output table."""
    columns = frame.columns.tolist()

    candidates = []

    if configured_name:
        candidates.append(configured_name)

    candidates.extend(aliases)

    # Exact match first.
    for candidate in candidates:
        if candidate in columns:
            return candidate

    # Case-insensitive exact match.
    folded = {
        str(column).casefold(): column
        for column in columns
    }

    for candidate in candidates:
        match = folded.get(
            str(candidate).casefold()
        )

        if match is not None:
            return match

    # Normalized match for differences such as sample_id/sampleid.
    normalized = {
        _normalize(column): column
        for column in columns
    }

    for candidate in candidates:
        match = normalized.get(
            _normalize(candidate)
        )

        if match is not None:
            return match

    raise ValueError(
        f"Could not resolve {label}. "
        f"Configured value: {configured_name!r}. "
        f"Available columns: {columns}"
    )


def resolve_sample_id_column(
    frame: pd.DataFrame,
    configured_name: str | None,
) -> str:
    return resolve_table_column(
        frame,
        configured_name,
        aliases=[
            "sample_id",
            "sampleid",
            "sampleID",
            "SampleID",
            "name",
            "ID",
        ],
        label="the isolate-ID column",
    )


def resolve_st_column(
    frame: pd.DataFrame,
    configured_name: str | None,
) -> str:
    return resolve_table_column(
        frame,
        configured_name,
        aliases=[
            "ST",
            "st_type",
            "sequence_type",
            "mlst",
        ],
        label="the sequence-type column",
    )


def _normalize(
    value: object,
) -> str:
    return "".join(
        character
        for character in str(value).casefold()
        if character.isalnum()
    )
