#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import pandas as pd

from configured_columns import (
    load_configured_columns,
    resolve_sample_id_column,
    resolve_table_column,
)


CLUSTER_COLOURS = {
    "1": "#f77189",
    "2": "#97a431",
    "3": "#36ada4",
    "4": "#a48cf4",
}

WARD_SHAPES = {
    "neonatal": "o",
    "other": "s",
}

COMPONENT_ANCHORS = [
    (-1.15, 0.00),
    (0.90, 0.72),
    (0.90, -0.10),
    (0.90, -0.88),
]

COMPONENT_SCALES = [
    1.00,
    0.48,
    0.35,
    0.35,
]


def normalise_label(value: object) -> str:
    text = str(value)

    if text.endswith(".0"):
        text = text[:-2]

    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a deterministic publication-quality static "
            "transmission network."
        )
    )

    parser.add_argument(
        "--nodes",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--edges",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--network-group",
        required=True,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=600,
    )

    parser.add_argument(
        "--outdir",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    args.outdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    nodes = pd.read_csv(
        args.nodes,
        dtype=str,
    )

    edges = pd.read_csv(
        args.edges,
        dtype=str,
    )

    nodes = nodes.loc[
        nodes["network_group"].eq(
            args.network_group
        )
    ].copy()

    edges = edges.loc[
        edges["network_group"].eq(
            args.network_group
        )
    ].copy()

    if nodes.empty:
        raise SystemExit(
            f"No nodes found for {args.network_group!r}."
        )

    node_id_column = (
        "sampleid"
        if "sampleid" in nodes.columns
        else "sample_id"
    )

    nodes[node_id_column] = (
        nodes[node_id_column]
        .astype(str)
    )

    nodes["Clusters"] = (
        nodes["Clusters"]
        .map(normalise_label)
    )

    edges["Clusters"] = (
        edges["Clusters"]
        .map(normalise_label)
    )

    graph = nx.Graph()

    for _, row in nodes.iterrows():
        graph.add_node(
            row[node_id_column],
            cluster=row["Clusters"],
            ward_type=str(
                row.get(
                    "ward_type",
                    "Missing",
                )
            ),
            st_type=str(
                row.get(
                    "st_type",
                    "",
                )
            ),
        )

    for _, row in edges.iterrows():
        graph.add_edge(
            str(row["sample_id_1"]),
            str(row["sample_id_2"]),
            snp_distance=float(
                row["snp_distance"]
            ),
            cluster=row["Clusters"],
            exceeds_days_cutoff=(
                str(
                    row.get(
                        "exceeds_days_cutoff",
                        "False",
                    )
                )
                .strip()
                .casefold()
                == "true"
            ),
        )

    cluster_order = sorted(
        nodes["Clusters"].unique(),
        key=lambda value: int(value),
    )

    positions: dict[str, tuple[float, float]] = {}

    for index, cluster in enumerate(
        cluster_order
    ):
        cluster_nodes = (
            nodes.loc[
                nodes["Clusters"].eq(cluster),
                node_id_column,
            ]
            .astype(str)
            .tolist()
        )

        subgraph = graph.subgraph(
            cluster_nodes
        ).copy()

        if len(cluster_nodes) == 1:
            local_positions = {
                cluster_nodes[0]: (
                    0.0,
                    0.0,
                )
            }
        else:
            local_positions = nx.spring_layout(
                subgraph,
                seed=args.seed + index,
                k=1.2 / max(
                    len(cluster_nodes) ** 0.5,
                    1.0,
                ),
                iterations=1000,
                weight=None,
            )

        anchor = COMPONENT_ANCHORS[
            min(
                index,
                len(COMPONENT_ANCHORS) - 1,
            )
        ]

        scale = COMPONENT_SCALES[
            min(
                index,
                len(COMPONENT_SCALES) - 1,
            )
        ]

        for node_id, coordinates in (
            local_positions.items()
        ):
            positions[node_id] = (
                anchor[0]
                + scale * float(
                    coordinates[0]
                ),
                anchor[1]
                + scale * float(
                    coordinates[1]
                ),
            )

    figure, axis = plt.subplots(
        figsize=(10, 7),
        constrained_layout=True,
    )

    axis.set_facecolor("white")

    # Draw edges by temporal-cutoff status.
    solid_edges = [
        (left, right)
        for left, right, data
        in graph.edges(data=True)
        if not data[
            "exceeds_days_cutoff"
        ]
    ]

    dashed_edges = [
        (left, right)
        for left, right, data
        in graph.edges(data=True)
        if data[
            "exceeds_days_cutoff"
        ]
    ]

    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=solid_edges,
        edge_color="#737373",
        width=1.5,
        style="solid",
        ax=axis,
    )

    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=dashed_edges,
        edge_color="#737373",
        width=1.5,
        style="dashed",
        ax=axis,
    )

    # Draw nodes by cluster and ward shape.
    for cluster in cluster_order:
        for ward_type, marker in (
            WARD_SHAPES.items()
        ):
            selected = (
                nodes.loc[
                    nodes["Clusters"].eq(cluster)
                    & nodes["ward_type"]
                    .fillna("Missing")
                    .astype(str)
                    .str.casefold()
                    .eq(ward_type),
                    node_id_column,
                ]
                .astype(str)
                .tolist()
            )

            if not selected:
                continue

            nx.draw_networkx_nodes(
                graph,
                positions,
                nodelist=selected,
                node_color=CLUSTER_COLOURS.get(
                    cluster,
                    "#999999",
                ),
                node_shape=marker,
                node_size=600,
                linewidths=1.2,
                edgecolors="#333333",
                ax=axis,
            )

    # Defensive drawing for unknown ward types.
    known_wards = set(
        WARD_SHAPES
    )

    unknown_nodes = (
        nodes.loc[
            ~nodes["ward_type"]
            .fillna("Missing")
            .astype(str)
            .str.casefold()
            .isin(known_wards),
            node_id_column,
        ]
        .astype(str)
        .tolist()
    )

    for node_id in unknown_nodes:
        cluster = str(
            graph.nodes[node_id][
                "cluster"
            ]
        )

        nx.draw_networkx_nodes(
            graph,
            positions,
            nodelist=[node_id],
            node_color=CLUSTER_COLOURS.get(
                cluster,
                "#999999",
            ),
            node_shape="D",
            node_size=600,
            linewidths=1.2,
            edgecolors="#333333",
            ax=axis,
        )

    nx.draw_networkx_labels(
        graph,
        positions,
        font_family="Arial",
        font_size=7,
        font_color="#222222",
        ax=axis,
    )

    edge_labels = {}

    for left, right, data in (
        graph.edges(data=True)
    ):
        distance = data[
            "snp_distance"
        ]

        edge_labels[
            (left, right)
        ] = (
            ""
            if distance == 0
            else f"{distance:g}"
        )

    nx.draw_networkx_edge_labels(
        graph,
        positions,
        edge_labels=edge_labels,
        font_family="Arial",
        font_size=6,
        font_color="#444444",
        rotate=False,
        label_pos=0.5,
        bbox={
            "boxstyle": "round,pad=0.08",
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.85,
        },
        ax=axis,
    )

    cluster_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markersize=8,
            markerfacecolor=(
                CLUSTER_COLOURS[
                    cluster
                ]
            ),
            markeredgecolor="#333333",
            label=f"Cluster {cluster}",
        )
        for cluster in cluster_order
    ]

    ward_handles = [
        Line2D(
            [0],
            [0],
            marker=marker,
            linestyle="none",
            markersize=8,
            markerfacecolor="#bdbdbd",
            markeredgecolor="#333333",
            label=ward_type,
        )
        for ward_type, marker
        in WARD_SHAPES.items()
    ]

    edge_handles = [
        Line2D(
            [0, 1],
            [0, 0],
            color="#737373",
            linewidth=1.5,
            linestyle="solid",
            label="Direct date difference ≤14 days",
        ),
        Line2D(
            [0, 1],
            [0, 0],
            color="#737373",
            linewidth=1.5,
            linestyle="dashed",
            label="Direct date difference >14 days",
        ),
    ]

    legend_clusters = axis.legend(
        handles=cluster_handles,
        title="Transmission cluster",
        loc="upper left",
        bbox_to_anchor=(1.01, 1.00),
        frameon=False,
        fontsize=8,
        title_fontsize=9,
    )

    axis.add_artist(
        legend_clusters
    )

    legend_wards = axis.legend(
        handles=ward_handles,
        title="Ward type",
        loc="upper left",
        bbox_to_anchor=(1.01, 0.62),
        frameon=False,
        fontsize=8,
        title_fontsize=9,
    )

    axis.add_artist(
        legend_wards
    )

    axis.legend(
        handles=edge_handles,
        title="Network edge",
        loc="upper left",
        bbox_to_anchor=(1.01, 0.34),
        frameon=False,
        fontsize=8,
        title_fontsize=9,
    )

    axis.set_title(
        (
            f"{args.network_group} "
            "transmission-cluster network\n"
            f"{nodes[node_id_column].nunique()} isolates · "
            f"{nodes['Clusters'].nunique()} clusters"
        ),
        loc="center",
        pad=16,
        fontfamily="Arial",
        fontsize=12,
        fontweight="bold",
    )

    axis.set_axis_off()

    base = (
        args.outdir
        / "Figure3C_transmission_network_Hospital_C"
    )

    figure.savefig(
        base.with_suffix(".png"),
        dpi=args.dpi,
        bbox_inches="tight",
        pad_inches=0.15,
        facecolor="white",
    )

    figure.savefig(
        base.with_suffix(".pdf"),
        bbox_inches="tight",
        pad_inches=0.15,
        facecolor="white",
    )

    figure.savefig(
        base.with_suffix(".svg"),
        bbox_inches="tight",
        pad_inches=0.15,
        facecolor="white",
    )

    plt.close(figure)

    print(
        f"Network exported to {args.outdir}"
    )


if __name__ == "__main__":
    main()
