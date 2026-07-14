#!/usr/bin/env python3
"""Generate a Markdown quality and scaling summary from normalized result CSV."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev


GroupKey = tuple[str, int, int, int]


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def coefficient_of_variation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    average = mean(values)
    return stdev(values) / average * 100.0 if average != 0.0 else None


def fmt(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cv-warning", default=10.0, type=float)
    args = parser.parse_args()

    rows = load_rows(args.input)
    if not rows:
        parser.error("input CSV contains no result rows")

    runtimes: dict[GroupKey, list[float]] = defaultdict(list)
    bandwidths: dict[GroupKey, list[float]] = defaultdict(list)
    for row in rows:
        key = (
            row["kernel"],
            int(row["elements"]),
            int(row["stride"]),
            int(row["threads"]),
        )
        runtimes[key].append(float(row["runtime_sec"]))
        bandwidths[key].append(float(row["bandwidth_gbps"]))

    machine_ids = sorted({row["machine_id"] for row in rows})
    sources = sorted({row["source_benchmark"] for row in rows})
    warning_groups: list[tuple[GroupKey, float]] = []
    table_rows: list[str] = []

    for key in sorted(runtimes):
        kernel, elements, stride, threads = key
        median_runtime = median(runtimes[key])
        median_bandwidth = median(bandwidths[key])
        cv = coefficient_of_variation(bandwidths[key])
        baseline = runtimes.get((kernel, elements, stride, 1))
        speedup = median(baseline) / median_runtime if baseline else None
        efficiency = speedup / threads if speedup is not None else None
        if cv is not None and cv > args.cv_warning:
            warning_groups.append((key, cv))
        workload = f"{kernel} / stride {stride}" if kernel == "strided" else kernel
        table_rows.append(
            f"| {workload} | {elements} | {elements * 8 / 1024**2:.3f} | {threads} | "
            f"{len(runtimes[key])} | {median_runtime:.6f} | {median_bandwidth:.3f} | "
            f"{fmt(cv, 2)} | {fmt(speedup, 2)} | {fmt(efficiency, 2)} |"
        )

    lines = [
        "# Benchmark Result Summary",
        "",
        f"- Input: `{args.input}`",
        f"- Machine IDs: {', '.join(f'`{value}`' for value in machine_ids)}",
        f"- Sources: {', '.join(f'`{value}`' for value in sources)}",
        f"- Result rows: {len(rows)}",
        f"- CV warning threshold: {args.cv_warning:.1f}%",
        "",
        "Medians are computed across independent repetitions. Speedup uses the median one-thread runtime for the same kernel, element count, and stride. Efficiency is speedup divided by thread count.",
        "",
        "| Workload | Elements | Array MiB | Threads | Reps | Median s | Median GB/s | CV % | Speedup | Efficiency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        *table_rows,
        "",
        "## Variation Warnings",
        "",
    ]
    if warning_groups:
        for (kernel, elements, stride, threads), cv in warning_groups:
            lines.append(
                f"- `{kernel}`, elements `{elements}`, stride `{stride}`, threads `{threads}`: CV {cv:.2f}%"
            )
    else:
        lines.append("- None.")
    lines.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
