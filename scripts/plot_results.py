#!/usr/bin/env python3
"""Generate dependency-free SVG plots from normalized benchmark CSV output."""

from __future__ import annotations

import argparse
import csv
import html
from collections import defaultdict
from pathlib import Path
from statistics import mean


COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]


def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def grouped_means(rows: list[dict], keys: tuple[str, ...], value: str) -> dict[tuple[str, ...], float]:
    groups: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in keys)].append(float(row[value]))
    return {key: mean(values) for key, values in groups.items()}


def nice_range(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    lo = min(values)
    hi = max(values)
    if lo == hi:
        pad = abs(lo) * 0.1 if lo != 0 else 1.0
        return lo - pad, hi + pad
    pad = (hi - lo) * 0.08
    return lo - pad, hi + pad


def svg_line_plot(
    title: str,
    xlabel: str,
    ylabel: str,
    series: list[tuple[str, list[tuple[float, float]]]],
    output: Path,
) -> None:
    width = 900
    height = 560
    left = 90
    right = 260
    top = 60
    bottom = 80
    plot_w = width - left - right
    plot_h = height - top - bottom

    all_x = [x for _, points in series for x, _ in points]
    all_y = [y for _, points in series for _, y in points]
    xmin, xmax = nice_range(all_x)
    ymin, ymax = nice_range(all_y)

    def sx(x: float) -> float:
        return left + (x - xmin) / (xmax - xmin) * plot_w

    def sy(y: float) -> float:
        return top + plot_h - (y - ymin) / (ymax - ymin) * plot_h

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-family="Arial" font-size="20">{html.escape(title)}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="black"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="black"/>',
    ]

    for i in range(6):
        tx = left + i * plot_w / 5
        xval = xmin + i * (xmax - xmin) / 5
        parts.append(f'<line x1="{tx:.1f}" y1="{top}" x2="{tx:.1f}" y2="{top + plot_h}" stroke="#e6e6e6"/>')
        parts.append(f'<text x="{tx:.1f}" y="{top + plot_h + 24}" text-anchor="middle" font-family="Arial" font-size="12">{xval:.3g}</text>')

        ty = top + i * plot_h / 5
        yval = ymax - i * (ymax - ymin) / 5
        parts.append(f'<line x1="{left}" y1="{ty:.1f}" x2="{left + plot_w}" y2="{ty:.1f}" stroke="#e6e6e6"/>')
        parts.append(f'<text x="{left - 10}" y="{ty + 4:.1f}" text-anchor="end" font-family="Arial" font-size="12">{yval:.3g}</text>')

    for idx, (label, points) in enumerate(series):
        if not points:
            continue
        color = COLORS[idx % len(COLORS)]
        coords = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in points)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in points:
            parts.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" fill="{color}"/>')
        legend_y = top + idx * 24
        legend_x = left + plot_w + 35
        parts.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 24}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{legend_x + 34}" y="{legend_y + 5}" font-family="Arial" font-size="13">{html.escape(label)}</text>')

    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 25}" text-anchor="middle" font-family="Arial" font-size="15">{html.escape(xlabel)}</text>')
    parts.append(
        f'<text transform="translate(24 {top + plot_h / 2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="15">{html.escape(ylabel)}</text>'
    )
    parts.append("</svg>")
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def plot_bandwidth_vs_threads(rows: list[dict], outdir: Path) -> None:
    data = grouped_means(rows, ("kernel", "elements", "threads"), "bandwidth_gbps")
    for kernel in sorted({row["kernel"] for row in rows}):
        series = []
        for elements in sorted({row["elements"] for row in rows if row["kernel"] == kernel}, key=int):
            points = [
                (float(threads), bandwidth)
                for (k, e, threads), bandwidth in data.items()
                if k == kernel and e == elements
            ]
            points.sort()
            series.append((f"{int(elements) * 8 / (1024 * 1024):.1f} MiB array", points))
        svg_line_plot(
            f"{kernel}: bandwidth vs. thread count",
            "Threads",
            "Effective bandwidth (GB/s)",
            series,
            outdir / f"{kernel}_bandwidth_vs_threads.svg",
        )


def plot_runtime_vs_size(rows: list[dict], outdir: Path) -> None:
    data = grouped_means(rows, ("kernel", "threads", "elements"), "runtime_sec")
    for kernel in sorted({row["kernel"] for row in rows}):
        series = []
        for threads in sorted({row["threads"] for row in rows if row["kernel"] == kernel}, key=int):
            points = [
                (float(int(elements) * 8 / (1024 * 1024)), runtime)
                for (k, t, elements), runtime in data.items()
                if k == kernel and t == threads
            ]
            points.sort()
            series.append((f"{threads} threads", points))
        svg_line_plot(
            f"{kernel}: runtime vs. working-set size",
            "Input array size (MiB)",
            "Runtime (s)",
            series,
            outdir / f"{kernel}_runtime_vs_size.svg",
        )


def plot_speedup_vs_threads(rows: list[dict], outdir: Path) -> None:
    runtime = grouped_means(rows, ("kernel", "elements", "threads"), "runtime_sec")
    for kernel in sorted({row["kernel"] for row in rows}):
        series = []
        for elements in sorted({row["elements"] for row in rows if row["kernel"] == kernel}, key=int):
            baseline = runtime.get((kernel, elements, "1"))
            if baseline is None:
                continue
            points = [
                (float(threads), baseline / value)
                for (k, e, threads), value in runtime.items()
                if k == kernel and e == elements
            ]
            points.sort()
            series.append((f"{int(elements) * 8 / (1024 * 1024):.1f} MiB array", points))
        svg_line_plot(
            f"{kernel}: speedup vs. thread count",
            "Threads",
            "Speedup over 1 thread",
            series,
            outdir / f"{kernel}_speedup_vs_threads.svg",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()

    rows = load_rows(args.input)
    args.outdir.mkdir(parents=True, exist_ok=True)
    plot_bandwidth_vs_threads(rows, args.outdir)
    plot_runtime_vs_size(rows, args.outdir)
    plot_speedup_vs_threads(rows, args.outdir)
    print(f"Wrote SVG plots to {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

