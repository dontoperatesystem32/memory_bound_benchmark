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

Run project commands from inside the benchmark repository:

```sh
cd memory_bound_benchmark
```

Serial build:

```sh
make
```

OpenMP build with Homebrew LLVM on macOS, after installing `llvm` and `libomp`:

```sh
make clean
make openmp CC=/opt/homebrew/opt/llvm/bin/clang
```

Linux LLVM/OpenMP build:

```sh
make clean
make openmp CC=clang
```

## Smoke Run

```sh
./bin/membench \
  --machine-id local \
  --kernel triad \
  --elements 1000000 \
  --threads 1 \
  --repetitions 3 \
  --csv results/smoke.csv
```

## Small Validation Run

Serial-only validation before OpenMP is configured:

```sh
python3 scripts/run_experiments.py \
  --config configs/mac_m4_serial_smoke.json \
  --binary ./bin/membench \
  --output results/mac_m4_serial_smoke.csv
```

OpenMP validation after building with `make openmp`:

```sh
python3 scripts/run_experiments.py \
  --config configs/mac_m4_local.json \
  --binary ./bin/membench \
  --output results/mac_m4_validation.csv
```

## Plot

```sh
python3 scripts/plot_results.py \
  --input results/mac_m4_validation.csv \
  --outdir plots/mac_m4_validation
```

## Cross-Machine Pipeline Gate

After an OpenMP build, run the compact schema-v2 gate before a full experiment. Use the appropriate machine ID on each system:

```sh
python3 scripts/run_experiments.py \
  --config configs/pipeline_v2_smoke.json \
  --machine-id intel_i5_12400f \
  --output results/intel_i5_12400f_pipeline_v2_smoke.csv

python3 scripts/plot_results.py \
  --input results/intel_i5_12400f_pipeline_v2_smoke.csv \
  --outdir plots/intel_i5_12400f_pipeline_v2_smoke
```

Inspect the full pilot matrix without running it:

```sh
python3 scripts/run_experiments.py \
  --config configs/pilot_memory_sweep.json \
  --machine-id intel_i5_12400f \
  --output results/intel_i5_12400f_pilot_memory_sweep.csv \
  --dry-run
```

The full sweep is run only after the compact gate passes on both machines.

## Official STREAM Baseline

Build and run official STREAM with LLVM/OpenMP, then normalize its output. Use the same repository-root workflow on every supported system:

```sh
python3 scripts/run_stream_baseline.py \
  --machine-id mac_m4_local \
  --cc /opt/homebrew/opt/llvm/bin/clang
```

On a system where LLVM Clang is available as `clang`:

```sh
python3 scripts/run_stream_baseline.py \
  --machine-id intel_i5_12400f \
  --cc clang
```

Run matching custom STREAM-style kernels:

```sh
python3 scripts/run_experiments.py \
  --config configs/mac_m4_custom_stream_compare.json \
  --binary ./bin/membench \
  --output results/custom_stream_mac_m4_compare.csv
```

Matching Intel custom STREAM-style run from inside the repository:

```sh
python3 scripts/run_experiments.py \
  --config configs/intel_i5_12400f_custom_stream_compare.json \
  --binary ./bin/membench \
  --output results/custom_stream_intel_i5_12400f_compare.csv
```

Compare official STREAM and custom STREAM-style bandwidths:

```sh
python3 scripts/compare_stream_custom.py \
  --stream results/stream_mac_m4_local_normalized.csv \
  --custom results/custom_stream_mac_m4_compare.csv \
  --output results/stream_vs_custom_mac_m4.md
```

## Machine Metadata

Collect machine, compiler, and benchmark-binary metadata:

```sh
python3 scripts/collect_metadata.py \
  --machine-id mac_m4_local \
  --output results/mac_m4_local_metadata.json \
  --summary-output results/mac_m4_local_metadata_summary.md \
  --compiler clang \
  --compiler /opt/homebrew/opt/llvm/bin/clang \
  --binary bin/membench
```

The JSON file is the full machine-readable record. The Markdown summary is intended for quick review and report drafting. Sensitive hardware identifiers from `system_profiler` are redacted by default.

## CSV Schema

Normalized rows use this schema:

```text
source_benchmark,machine_id,kernel,elements,bytes,stride,threads,repetition,warmups,iterations,runtime_sec,bandwidth_gbps,checksum,compiler,compiler_flags
```

`warmups` records untimed kernel calls before measurement. `iterations` is the number of kernel calls batched inside one timed repetition. `bytes` records total useful bytes across that batch.
