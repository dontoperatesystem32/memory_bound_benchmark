# Established Benchmark Integrations

This project should use established memory benchmarks where they add value. The first custom executable exists to provide controlled kernels and a unified CSV format; it is not meant to replace all established tools.

## STREAM

Official STREAM site:

```text
https://www.cs.virginia.edu/stream/
```

STREAM is the baseline reference for sustainable memory bandwidth using Copy, Scale, Add, and Triad. Use it to sanity-check custom STREAM-style kernels and to provide a recognized baseline in reports.

Integration path:

1. Keep the official source files under `benchmark_suite/external/stream/`.
2. Build and run with Homebrew LLVM/OpenMP using `benchmark_suite/scripts/run_stream_baseline.py`.
3. Save raw output under `benchmark_suite/results/raw_stream_*.txt`.
4. Normalize it with `benchmark_suite/scripts/normalize_stream.py`.

Mac validation command:

```sh
python3 benchmark_suite/scripts/run_stream_baseline.py
```

Example normalization:

```sh
python3 benchmark_suite/scripts/normalize_stream.py \
  --input benchmark_suite/results/raw_stream_mac_m4.txt \
  --output benchmark_suite/results/normalized_stream_mac_m4.csv \
  --machine-id mac_m4_local \
  --elements 10000000 \
  --threads 4 \
  --compiler clang \
  --compiler-flags "-O3 -fopenmp"
```

## BabelStream

BabelStream repository:

```text
https://github.com/UoB-HPC/BabelStream
```

BabelStream may be useful later as a second established benchmark family, especially if comparing methodology or multi-backend behavior. It is not required for the first validation run.
