#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
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

MARKERS = ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h", "8", "*"]
COLOURS = [
    "#f77189", "#97a431", "#36ada4", "#a48cf4", "#e68310", "#3ba3ec",
    "#de8f05", "#6f4c9b", "#11a579", "#3969ac", "#f2b701", "#e73f74",
]


def natural_key(value: object) -> list[object]:
    return [int(x) if x.isdigit() else x.casefold() for x in re.split(r"(\d+)", str(value))]


def norm(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def safe_name(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip()).strip("_") or "network"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a deterministic static transmission network using the analysis YAML."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--nodes", required=True, type=Path)
    parser.add_argument("--edges", required=True, type=Path)
    parser.add_argument("--network-group", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--width", type=float, default=10.0)
    parser.add_argument("--height", type=float, default=7.0)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--output-prefix", default=None)
    return parser.parse_args()


def positions_by_cluster(graph: nx.Graph, nodes: pd.DataFrame, id_col: str,
                         cluster_col: str, clusters: list[str], seed: int):
    positions: dict[str, tuple[float, float]] = {}
    n_clusters = max(len(clusters), 1)
    radius = 1.35 if n_clusters > 1 else 0.0
    for index, cluster in enumerate(clusters):
        members = nodes.loc[nodes[cluster_col].eq(cluster), id_col].astype(str).tolist()
        subgraph = graph.subgraph(members).copy()
        if len(members) == 1:
            local = {members[0]: (0.0, 0.0)}
        else:
            local = nx.spring_layout(
                subgraph,
                seed=seed + index,
                k=1.25 / max(len(members) ** 0.5, 1.0),
                iterations=1000,
                weight=None,
            )
        angle = 2.0 * 3.141592653589793 * index / n_clusters
        anchor = (radius * __import__("math").cos(angle), radius * __import__("math").sin(angle))
        scale = 0.72 if n_clusters <= 3 else 0.52
        for node_id, xy in local.items():
            positions[node_id] = (anchor[0] + scale * float(xy[0]), anchor[1] + scale * float(xy[1]))
    return positions


def main() -> None:
    args = parse_args()
    for path in (args.config, args.nodes, args.edges):
        if not path.exists():
            raise SystemExit(f"Missing required input: {path}")

    schema = load_configured_columns(args.config)
    nodes_all = pd.read_csv(args.nodes, dtype=str)
    edges_all = pd.read_csv(args.edges, dtype=str)

    node_group = resolve_table_column(nodes_all, "network_group", aliases=["group", "network"], label="node network-group column")
    edge_group = resolve_table_column(edges_all, "network_group", aliases=["group", "network"], label="edge network-group column")

    nodes = nodes_all.loc[nodes_all[node_group].astype(str).eq(args.network_group)].copy()
    edges = edges_all.loc[edges_all[edge_group].astype(str).eq(args.network_group)].copy()
    if nodes.empty:
        available = sorted(nodes_all[node_group].dropna().astype(str).unique().tolist(), key=natural_key)
        raise SystemExit(f"No nodes found for {args.network_group!r}. Available groups: {available}")

    id_col = resolve_sample_id_column(nodes, schema.sample_id)
    shape_col = resolve_table_column(
        nodes,
        schema.secondary_var,
        aliases=["ward_type", "FacilityCode", "facility_code", "Community", "community"],
        label="variables.var_01 node-shape column",
    )
    node_cluster = resolve_table_column(nodes, "Clusters", aliases=["cluster", "transmission_cluster"], label="node cluster column")
    edge_cluster = resolve_table_column(edges, "Clusters", aliases=["cluster", "transmission_cluster"], label="edge cluster column")
    source_col = resolve_table_column(edges, "sample_id_1", aliases=["sampleid_1", "source", "node_1", "X1"], label="edge source column")
    target_col = resolve_table_column(edges, "sample_id_2", aliases=["sampleid_2", "target", "node_2", "X2"], label="edge target column")
    distance_col = resolve_table_column(edges, "snp_distance", aliases=["SNPs", "distance", "weight", "X3"], label="SNP-distance column")
    exceeded_col = next((c for c in ["exceeds_days_cutoff", "days_cutoff_exceeded"] if c in edges.columns), None)

    nodes[id_col] = nodes[id_col].astype(str)
    nodes[node_cluster] = nodes[node_cluster].map(norm)
    nodes[shape_col] = nodes[shape_col].fillna("Missing").astype(str)
    edges[edge_cluster] = edges[edge_cluster].map(norm)

    clusters = sorted(nodes[node_cluster].dropna().unique().tolist(), key=natural_key)
    shapes = sorted(nodes[shape_col].dropna().unique().tolist(), key=natural_key)
    if len(shapes) > len(MARKERS):
        raise SystemExit(f"{shape_col!r} has {len(shapes)} categories; supported maximum is {len(MARKERS)}.")

    colours = {value: COLOURS[i % len(COLOURS)] for i, value in enumerate(clusters)}
    markers = {value: MARKERS[i] for i, value in enumerate(shapes)}

    graph = nx.Graph()
    for _, row in nodes.iterrows():
        graph.add_node(str(row[id_col]), cluster=row[node_cluster], shape=row[shape_col])
    for _, row in edges.iterrows():
        source, target = str(row[source_col]), str(row[target_col])
        if source not in graph or target not in graph:
            continue
        exceeded = False if exceeded_col is None else str(row[exceeded_col]).strip().casefold() in {"true", "1", "yes"}
        graph.add_edge(source, target, snp_distance=float(row[distance_col]), exceeds_days_cutoff=exceeded)

    positions = positions_by_cluster(graph, nodes, id_col, node_cluster, clusters, args.seed)
    figure, axis = plt.subplots(figsize=(args.width, args.height), constrained_layout=True)
    axis.set_facecolor("white")

    solid = [(a, b) for a, b, d in graph.edges(data=True) if not d["exceeds_days_cutoff"]]
    dashed = [(a, b) for a, b, d in graph.edges(data=True) if d["exceeds_days_cutoff"]]
    nx.draw_networkx_edges(graph, positions, edgelist=solid, edge_color="#737373", width=1.5, style="solid", ax=axis)
    nx.draw_networkx_edges(graph, positions, edgelist=dashed, edge_color="#737373", width=1.5, style="dashed", ax=axis)

    for cluster in clusters:
        for shape in shapes:
            selected = nodes.loc[nodes[node_cluster].eq(cluster) & nodes[shape_col].eq(shape), id_col].astype(str).tolist()
            if selected:
                nx.draw_networkx_nodes(
                    graph, positions, nodelist=selected, node_color=colours[cluster],
                    node_shape=markers[shape], node_size=600, linewidths=1.2,
                    edgecolors="#333333", ax=axis,
                )

    nx.draw_networkx_labels(graph, positions, font_family="Arial", font_size=7, font_color="#222222", ax=axis)
    edge_labels = {(a, b): "" if d["snp_distance"] == 0 else f'{d["snp_distance"]:g}' for a, b, d in graph.edges(data=True)}
    nx.draw_networkx_edge_labels(
        graph, positions, edge_labels=edge_labels, font_family="Arial", font_size=6,
        font_color="#444444", rotate=False, label_pos=0.5,
        bbox={"boxstyle": "round,pad=0.08", "facecolor": "white", "edgecolor": "none", "alpha": 0.85}, ax=axis,
    )

    cluster_handles = [Line2D([0], [0], marker="o", linestyle="none", markersize=8, markerfacecolor=colours[c], markeredgecolor="#333333", label=f"Cluster {c}") for c in clusters]
    shape_handles = [Line2D([0], [0], marker=markers[s], linestyle="none", markersize=8, markerfacecolor="#bdbdbd", markeredgecolor="#333333", label=s) for s in shapes]
    cutoff = schema.days_cutoff
    edge_handles = [
        Line2D([0, 1], [0, 0], color="#737373", linewidth=1.5, linestyle="solid", label=f"Direct date difference ≤{cutoff:g} days" if cutoff is not None else "Within temporal cutoff"),
        Line2D([0, 1], [0, 0], color="#737373", linewidth=1.5, linestyle="dashed", label=f"Direct date difference >{cutoff:g} days" if cutoff is not None else "Above temporal cutoff"),
    ]

    legend1 = axis.legend(handles=cluster_handles, title="Transmission cluster", loc="upper left", bbox_to_anchor=(1.01, 1.00), frameon=False, fontsize=8, title_fontsize=9)
    axis.add_artist(legend1)
    legend2 = axis.legend(handles=shape_handles, title=shape_col, loc="upper left", bbox_to_anchor=(1.01, 0.64), frameon=False, fontsize=8, title_fontsize=9)
    axis.add_artist(legend2)
    axis.legend(handles=edge_handles, title="Network edge", loc="upper left", bbox_to_anchor=(1.01, 0.32), frameon=False, fontsize=8, title_fontsize=9)

    axis.set_title(
        f"{args.network_group} transmission-cluster network\n{nodes[id_col].nunique()} isolates · {nodes[node_cluster].nunique()} clusters",
        loc="center", pad=16, fontfamily="Arial", fontsize=12, fontweight="bold",
    )
    axis.set_axis_off()

    args.outdir.mkdir(parents=True, exist_ok=True)
    prefix = args.output_prefix or f"transmission_network_{safe_name(args.network_group)}"
    base = args.outdir / prefix
    figure.savefig(base.with_suffix(".png"), dpi=args.dpi, bbox_inches="tight", pad_inches=0.15, facecolor="white")
    figure.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.15, facecolor="white")
    figure.savefig(base.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.15, facecolor="white")
    plt.close(figure)

    print("Config:", args.config)
    print("Network group:", args.network_group)
    print("Sample ID column:", id_col)
    print("Shape column:", shape_col)
    print("Shape categories:", shapes)
    print("Transmission clusters:", clusters)
    print("Isolates:", nodes[id_col].nunique())
    print("Edges:", graph.number_of_edges())
    print("Output base:", base)


if __name__ == "__main__":
    main()
