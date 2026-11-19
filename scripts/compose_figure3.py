#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


LAYOUT_VERSION = "scatter-left-top_heatmap-right_network-left-bottom_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble the publication Figure 3 composite."
        )
    )

    parser.add_argument(
        "--heatmap",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--scatter",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--network",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--outdir",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=600,
    )

    return parser.parse_args()


def crop_white(
    image: Image.Image,
    margin: int = 60,
) -> Image.Image:
    rgb = image.convert("RGB")
    array = np.asarray(rgb)

    content = np.any(
        array < 248,
        axis=2,
    )

    coordinates = np.argwhere(
        content
    )

    if coordinates.size == 0:
        return rgb

    top, left = coordinates.min(
        axis=0
    )

    bottom, right = coordinates.max(
        axis=0
    )

    left = max(
        int(left) - margin,
        0,
    )

    top = max(
        int(top) - margin,
        0,
    )

    right = min(
        int(right) + margin + 1,
        rgb.width,
    )

    bottom = min(
        int(bottom) + margin + 1,
        rgb.height,
    )

    return rgb.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )


def add_panel(
    axis,
    image_path: Path,
    panel_label: str,
) -> None:
    image = crop_white(
        Image.open(image_path)
    )

    axis.imshow(image)

    axis.text(
        -0.015,
        1.025,
        panel_label,
        transform=axis.transAxes,
        ha="left",
        va="bottom",
        fontsize=18,
        fontfamily="Arial",
        fontweight="bold",
        color="#111111",
        clip_on=False,
    )

    axis.set_axis_off()


def main() -> None:
    args = parse_args()

    for path in (
        args.heatmap,
        args.scatter,
        args.network,
    ):
        if not path.exists():
            raise SystemExit(
                f"Missing panel: {path}"
            )

    args.outdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure = plt.figure(
        figsize=(16, 10.5),
        constrained_layout=True,
    )

    grid = figure.add_gridspec(
        nrows=2,
        ncols=2,
        height_ratios=[
            0.72,
            1.28,
        ],
        width_ratios=[
            1.00,
            1.32,
        ],
        wspace=0.025,
        hspace=0.045,
    )

    # Panel A: temporal scatterplot in the upper-left panel.
    axis_a = figure.add_subplot(
        grid[0, 0]
    )

    # Panel B: genomic heatmap spans the full right column.
    axis_b = figure.add_subplot(
        grid[:, 1]
    )

    # Panel C: transmission network in the lower-left panel.
    axis_c = figure.add_subplot(
        grid[1, 0]
    )

    axis_a.set_anchor("C")
    axis_b.set_anchor("C")
    axis_c.set_anchor("C")

    add_panel(
        axis_a,
        args.scatter,
        "A",
    )

    add_panel(
        axis_b,
        args.heatmap,
        "B",
    )

    add_panel(
        axis_c,
        args.network,
        "C",
    )

    base = (
        args.outdir
        / "Figure3_Hospital_C_Facility_analysis"
    )

    figure.savefig(
        base.with_suffix(".png"),
        dpi=args.dpi,
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="white",
    )

    figure.savefig(
        base.with_suffix(".pdf"),
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="white",
    )

    figure.savefig(
        base.with_suffix(".svg"),
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="white",
    )

    plt.close(figure)

    print(
        f"Figure 3 exported to {args.outdir}"
    )
    print(
        f"Layout version: {LAYOUT_VERSION}"
    )


if __name__ == "__main__":
    main()
