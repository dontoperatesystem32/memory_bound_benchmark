#!/usr/bin/env python3
"""Run a small validation matrix for the custom memory-bound benchmark executable."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--binary", default="benchmark_suite/bin/membench", type=Path)
    args = parser.parse_args()

    config = load_config(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.output.exists():
        args.output.unlink()

    kernels = config["experiment"]["kernels"]
    elements = config["experiment"]["elements"]
    threads = config["experiment"]["threads"]
    repetitions = int(config["experiment"]["repetitions"])
    strides = config["experiment"].get("strides", {"strided": 16})

    for kernel in kernels:
        for n in elements:
            for thread_count in threads:
                command = [
                    str(args.binary),
                    "--machine-id",
                    config["machine_id"],
                    "--kernel",
                    kernel,
                    "--elements",
                    str(n),
                    "--threads",
                    str(thread_count),
                    "--repetitions",
                    str(repetitions),
                    "--csv",
                    str(args.output),
                ]
                if kernel == "strided":
                    command.extend(["--stride", str(strides.get("strided", 16))])
                subprocess.run(command, check=True)

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

