#!/usr/bin/env python3
"""Run a configured matrix for the custom memory-bound benchmark executable."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--binary", default=PROJECT_ROOT / "bin/membench", type=Path)
    parser.add_argument("--machine-id", help="Override machine_id from the configuration.")
    parser.add_argument("--dry-run", action="store_true", help="Print the matrix without executing it.")
    args = parser.parse_args()

    config = load_config(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.output.exists() and not args.dry_run:
        args.output.unlink()

    kernels = config["experiment"]["kernels"]
    elements = config["experiment"]["elements"]
    threads = config["experiment"]["threads"]
    repetitions = int(config["experiment"]["repetitions"])
    warmups = int(config["experiment"].get("warmups", 1))
    strides = config["experiment"].get("strides", {"strided": 16})
    iterations = config["experiment"].get("iterations", 1)
    kernel_threads = config["experiment"].get("kernel_threads", {})
    machine_id = args.machine_id or config.get("machine_id")
    if not machine_id:
        parser.error("machine ID is required via --machine-id or the configuration")

    environment = os.environ.copy()
    for key, value in config.get("environment", {}).items():
        environment[str(key)] = str(value)

    def iterations_for(element_count: int) -> int:
        if isinstance(iterations, dict):
            return int(iterations.get(str(element_count), 1))
        return int(iterations)

    def strides_for(kernel: str) -> list[int]:
        if kernel != "strided":
            return [1]
        configured = strides.get("strided", 16)
        if isinstance(configured, list):
            return [int(value) for value in configured]
        return [int(configured)]

    jobs: list[tuple[str, int, int, int, int]] = []
    for kernel in kernels:
        for n in elements:
            selected_threads = kernel_threads.get(kernel, threads)
            for stride in strides_for(kernel):
                for thread_count in selected_threads:
                    jobs.append((kernel, int(n), int(stride), int(thread_count), iterations_for(int(n))))

    shuffle_seed = config["experiment"].get("shuffle_seed")
    if shuffle_seed is not None:
        random.Random(int(shuffle_seed)).shuffle(jobs)
        print(f"Job order shuffled with seed {shuffle_seed}", flush=True)

    print(
        f"Matrix: {len(jobs)} process invocations, "
        f"{len(jobs) * repetitions} result rows, {repetitions} repetitions per invocation",
        flush=True,
    )

    for index, (kernel, n, stride, thread_count, iteration_count) in enumerate(jobs, start=1):
        print(
            f"[{index}/{len(jobs)}] kernel={kernel} elements={n} stride={stride} "
            f"threads={thread_count} iterations={iteration_count}",
            flush=True,
        )
        if args.dry_run:
            continue
        command = [
            str(args.binary),
            "--machine-id",
            machine_id,
            "--kernel",
            kernel,
            "--elements",
            str(n),
            "--threads",
            str(thread_count),
            "--repetitions",
            str(repetitions),
            "--iterations",
            str(iteration_count),
            "--warmups",
            str(warmups),
            "--stride",
            str(stride),
            "--csv",
            str(args.output),
        ]
        subprocess.run(command, check=True, env=environment)

    if args.dry_run:
        return 0

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
