#!/usr/bin/env python3
"""Build and run official STREAM from this repository, then normalize output."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CLANG = (
    "/opt/homebrew/opt/llvm/bin/clang"
    if Path("/opt/homebrew/opt/llvm/bin/clang").exists()
    else "clang"
)


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, stdout: Path | None = None) -> None:
    if stdout is None:
        subprocess.run(command, cwd=cwd, env=env, check=True)
        return
    stdout.parent.mkdir(parents=True, exist_ok=True)
    with stdout.open("w", encoding="utf-8") as f:
        subprocess.run(command, cwd=cwd, env=env, check=True, stdout=f, stderr=subprocess.STDOUT)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and run official STREAM using the benchmark repository workflow."
    )
    parser.add_argument("--machine-id", required=True)
    parser.add_argument("--stream-dir", default=PROJECT_ROOT / "external/stream", type=Path)
    parser.add_argument("--results-dir", default=PROJECT_ROOT / "results", type=Path)
    parser.add_argument("--cc", default=DEFAULT_CLANG)
    parser.add_argument("--array-size", default=20_000_000, type=int)
    parser.add_argument("--ntimes", default=10, type=int)
    parser.add_argument("--threads", nargs="+", default=[1, 2, 4], type=int)
    parser.add_argument("--normalized-output", type=Path)
    args = parser.parse_args()

    normalized_output = args.normalized_output or (
        args.results_dir / f"stream_{args.machine_id}_normalized.csv"
    )

    build_dir = args.stream_dir / "build"
    binary = build_dir / f"stream_{args.array_size}_{args.ntimes}"
    build_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    if normalized_output.exists():
        normalized_output.unlink()

    flags = [
        "-O3",
        "-fopenmp",
        f"-DSTREAM_ARRAY_SIZE={args.array_size}",
        f"-DNTIMES={args.ntimes}",
    ]
    compile_command = [
        args.cc,
        *flags,
        str(args.stream_dir / "stream.c"),
        "-o",
        str(binary),
    ]
    print("Compiling official STREAM:")
    print(" ".join(compile_command))
    run(compile_command)

    compiler_version = subprocess.run([args.cc, "--version"], check=True, text=True, capture_output=True).stdout.splitlines()[0]
    compiler_flags = " ".join(flags)

    for thread_count in args.threads:
        raw_output = args.results_dir / f"raw_stream_{args.machine_id}_threads_{thread_count}.txt"
        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = str(thread_count)
        env["OMP_PROC_BIND"] = env.get("OMP_PROC_BIND", "false")
        print(f"Running official STREAM with OMP_NUM_THREADS={thread_count}")
        run([str(binary)], env=env, stdout=raw_output)
        run(
            [
                "python3",
                str(PROJECT_ROOT / "scripts/normalize_stream.py"),
                "--input",
                str(raw_output),
                "--output",
                str(normalized_output),
                "--machine-id",
                args.machine_id,
                "--elements",
                str(args.array_size),
                "--threads",
                str(thread_count),
                "--compiler",
                compiler_version,
                "--compiler-flags",
                compiler_flags,
            ]
        )

    print(f"Wrote normalized STREAM CSV to {normalized_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
