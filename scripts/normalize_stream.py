#!/usr/bin/env python3
"""Normalize official STREAM text output into the project CSV schema.

The official STREAM benchmark reports best/min/avg/max times per kernel. This
normalizer emits one row per STREAM kernel using the best-rate and minimum-time
fields. It is intended for integrating STREAM runs into the same analysis
pipeline as the custom kernels.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


STREAM_ROW = re.compile(
    r"^(Copy|Scale|Add|Triad):\s+"
    r"(?P<rate>[0-9.]+)\s+"
    r"(?P<avg>[0-9.]+)\s+"
    r"(?P<min>[0-9.]+)\s+"
    r"(?P<max>[0-9.]+)"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--machine-id", required=True)
    parser.add_argument("--elements", required=True, type=int)
    parser.add_argument("--threads", required=True, type=int)
    parser.add_argument("--compiler", default="unknown")
    parser.add_argument("--compiler-flags", default="unknown")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not args.output.exists() or args.output.stat().st_size == 0

    with args.input.open("r", encoding="utf-8", errors="replace") as src, args.output.open(
        "a", encoding="utf-8", newline=""
    ) as dst:
        writer = csv.writer(dst)
        if needs_header:
            writer.writerow(
                [
                    "source_benchmark",
                    "machine_id",
                    "kernel",
                    "elements",
                    "bytes",
                    "stride",
                    "threads",
                    "repetition",
                    "runtime_sec",
                    "bandwidth_gbps",
                    "checksum",
                    "compiler",
                    "compiler_flags",
                ]
            )
        for line in src:
            match = STREAM_ROW.match(line.strip())
            if not match:
                continue
            kernel = match.group(1).lower()
            bytes_per_element = 16 if kernel in {"copy", "scale"} else 24
            writer.writerow(
                [
                    "stream",
                    args.machine_id,
                    kernel,
                    args.elements,
                    args.elements * bytes_per_element,
                    1,
                    args.threads,
                    "best",
                    match.group("min"),
                    float(match.group("rate")) / 1000.0,
                    "not_reported",
                    args.compiler,
                    args.compiler_flags,
                ]
            )

    print(f"Normalized STREAM output into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
