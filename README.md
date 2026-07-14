# Hybrid Memory-Bound Benchmark Pipeline

This directory contains a reproducible benchmark and analysis pipeline for studying memory-bound CPU behavior across ARM64 and x86-64 systems.

The project is not intended to prove that one architecture is generally superior. It measures workload-specific behavior under explicit conditions: kernel, working-set size, thread count, compiler, runtime, and machine configuration.

## Current Contents

- `src/` and `include/`: custom memory-bound kernels and shared utilities.
- `external/`: integration notes and parsers for established benchmarks such as STREAM.
- `scripts/`: runners, metadata collection, normalization, and plotting.
- `configs/`: machine/compiler configuration templates.
- `results/`: CSV output from benchmark runs.
- `plots/`: generated figures.
- `docs/`: methodology notes.

## Build

Serial build:

```sh
make -C benchmark_suite
```

OpenMP build with Homebrew LLVM on macOS, after installing `llvm` and `libomp`:

```sh
make -C benchmark_suite clean
make -C benchmark_suite openmp CC=/opt/homebrew/opt/llvm/bin/clang
```

Linux LLVM/OpenMP build:

```sh
make -C benchmark_suite clean
make -C benchmark_suite openmp CC=clang
```

## Smoke Run

```sh
benchmark_suite/bin/membench \
  --machine-id local \
  --kernel triad \
  --elements 1000000 \
  --threads 1 \
  --repetitions 3 \
  --csv benchmark_suite/results/smoke.csv
```

## Small Validation Run

Serial-only validation before OpenMP is configured:

```sh
python3 benchmark_suite/scripts/run_experiments.py \
  --config benchmark_suite/configs/mac_m4_serial_smoke.json \
  --output benchmark_suite/results/mac_m4_serial_smoke.csv
```

OpenMP validation after building with `make openmp`:

```sh
python3 benchmark_suite/scripts/run_experiments.py \
  --config benchmark_suite/configs/mac_m4_local.json \
  --output benchmark_suite/results/mac_m4_validation.csv
```

## Plot

```sh
python3 benchmark_suite/scripts/plot_results.py \
  --input benchmark_suite/results/mac_m4_validation.csv \
  --outdir benchmark_suite/plots
```

## Official STREAM Baseline

Build and run official STREAM with Homebrew LLVM/OpenMP, then normalize its output:

```sh
python3 benchmark_suite/scripts/run_stream_baseline.py
```

Run matching custom STREAM-style kernels:

```sh
python3 benchmark_suite/scripts/run_experiments.py \
  --config benchmark_suite/configs/mac_m4_custom_stream_compare.json \
  --output benchmark_suite/results/custom_stream_mac_m4_compare.csv
```

Compare official STREAM and custom STREAM-style bandwidths:

```sh
python3 benchmark_suite/scripts/compare_stream_custom.py \
  --stream benchmark_suite/results/stream_mac_m4_normalized.csv \
  --custom benchmark_suite/results/custom_stream_mac_m4_compare.csv \
  --output benchmark_suite/results/stream_vs_custom_mac_m4.md
```

## Machine Metadata

Collect machine, compiler, and benchmark-binary metadata:

```sh
python3 benchmark_suite/scripts/collect_metadata.py \
  --machine-id mac_m4_local \
  --output benchmark_suite/results/mac_m4_local_metadata.json \
  --summary-output benchmark_suite/results/mac_m4_local_metadata_summary.md \
  --compiler clang \
  --compiler /opt/homebrew/opt/llvm/bin/clang \
  --binary benchmark_suite/bin/membench
```

The JSON file is the full machine-readable record. The Markdown summary is intended for quick review and report drafting. Sensitive hardware identifiers from `system_profiler` are redacted by default.

## CSV Schema

Normalized rows use this schema:

```text
source_benchmark,machine_id,kernel,elements,bytes,stride,threads,repetition,runtime_sec,bandwidth_gbps,checksum,compiler,compiler_flags
```
