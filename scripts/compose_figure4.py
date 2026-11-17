#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

LAYOUT_VERSION = "st802_top_st5541_bottom_scatter_left_network_right_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble the publication Figure 4 composite."
    )
    parser.add_argument("--st802-scatter", required=True, type=Path)
    parser.add_argument("--st802-network", required=True, type=Path)
    parser.add_argument("--st5541-scatter", required=True, type=Path)
    parser.add_argument("--st5541-network", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--width", type=float, default=14.0)
    parser.add_argument("--height", type=float, default=10.5)
    return parser.parse_args()


def crop_white(image: Image.Image, margin: int = 36) -> Image.Image:
    rgb = image.convert("RGB")
    array = np.asarray(rgb)
    content = np.any(array < 248, axis=2)
    coordinates = np.argwhere(content)
    if coordinates.size == 0:
        return rgb

    top, left = coordinates.min(axis=0)
    bottom, right = coordinates.max(axis=0)
    left = max(int(left) - margin, 0)
    top = max(int(top) - margin, 0)
    right = min(int(right) + margin + 1, rgb.width)
    bottom = min(int(bottom) + margin + 1, rgb.height)
    return rgb.crop((left, top, right, bottom))


def add_panel(axis, image_path: Path, panel_label: str) -> None:
    image = crop_white(Image.open(image_path))
    axis.imshow(image)
    axis.text(
        -0.012,
        1.022,
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
    axis.set_anchor("C")
    axis.set_axis_off()


def main() -> None:
    args = parse_args()
    inputs = (
        args.st802_scatter,
        args.st802_network,
        args.st5541_scatter,
        args.st5541_network,
    )
    for path in inputs:
        if not path.exists():
            raise SystemExit(f"Missing panel: {path}")

    args.outdir.mkdir(parents=True, exist_ok=True)

    figure = plt.figure(
        figsize=(args.width, args.height),
        constrained_layout=True,
    )
    grid = figure.add_gridspec(
        nrows=2,
        ncols=2,
        width_ratios=[1.12, 1.00],
        height_ratios=[1.00, 1.00],
        wspace=0.035,
        hspace=0.060,
    )

    axis_a = figure.add_subplot(grid[0, 0])
    axis_b = figure.add_subplot(grid[0, 1])
    axis_c = figure.add_subplot(grid[1, 0])
    axis_d = figure.add_subplot(grid[1, 1])

    add_panel(axis_a, args.st802_scatter, "A")
    add_panel(axis_b, args.st802_network, "B")
    add_panel(axis_c, args.st5541_scatter, "C")
    add_panel(axis_d, args.st5541_network, "D")

    base = args.outdir / "Figure4_Ghana_Community_analysis"
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

    print(f"Figure 4 exported to {args.outdir}")
    print(f"Layout version: {LAYOUT_VERSION}")


if __name__ == "__main__":
    main()
