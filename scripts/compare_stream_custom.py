#!/usr/bin/env python3
"""Compare official STREAM rows with custom STREAM-style kernel rows."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


KERNELS = ("copy", "scale", "add", "triad")


def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def best_bandwidth(rows: list[dict], source: str) -> dict[tuple[str, str], float]:
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        if row["source_benchmark"] == source and row["kernel"] in KERNELS:
            groups[(row["kernel"], row["threads"])].append(float(row["bandwidth_gbps"]))
    return {key: max(values) for key, values in groups.items()}


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream", required=True, type=Path)
    parser.add_argument("--custom", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    stream = best_bandwidth(load_rows(args.stream), "stream")
    custom = best_bandwidth(load_rows(args.custom), "custom")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        f.write("# Official STREAM vs Custom STREAM-Style Kernels\n\n")
        f.write("Bandwidth values are best observed values over available rows in GB/s. This matches STREAM's convention of reporting best bandwidth after repeated runs. Differences are descriptive only; official STREAM and the custom kernels are not claimed to be identical implementations.\n\n")
        f.write("| Kernel | Threads | STREAM GB/s | Custom GB/s | Custom/STREAM |\n")
        f.write("|---|---:|---:|---:|---:|\n")
        for kernel in KERNELS:
            thread_values = sorted({threads for k, threads in set(stream) | set(custom) if k == kernel}, key=int)
            for threads in thread_values:
                s = stream.get((kernel, threads))
                c = custom.get((kernel, threads))
                ratio = c / s if s and c else None
                f.write(
                    f"| {kernel} | {threads} | "
                    f"{fmt(s)} | "
                    f"{fmt(c)} | "
                    f"{fmt(ratio)} |\n"
                )

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
