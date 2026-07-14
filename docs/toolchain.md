# Toolchain Notes

The preferred compiler family for this project is LLVM/Clang on both machines. This follows the supervisor's comment that compiler differences should be reduced where possible.

## macOS ARM64

The system `clang` is Apple Clang. It can build the serial benchmark executable, but it does not support `-fopenmp` in this environment:

```text
clang: error: unsupported option '-fopenmp'
```

For OpenMP experiments, install Homebrew LLVM and `libomp`, then build with:

```sh
make -C benchmark_suite clean
make -C benchmark_suite openmp CC=/opt/homebrew/opt/llvm/bin/clang
```

## Intel x86-64 PC

Use LLVM/Clang with an OpenMP runtime where possible. GCC is acceptable as a fallback only if LLVM setup blocks progress. Compiler differences must be recorded in metadata and CSV output.

## Current Rule

If the executable is built without OpenMP, it rejects `--threads` values other than `1`. This prevents accidental creation of misleading multi-threaded rows from a serial binary.

## Metadata Check

After building the benchmark, collect metadata with both Apple Clang and Homebrew Clang recorded:

```sh
python3 benchmark_suite/scripts/collect_metadata.py \
  --machine-id mac_m4_local \
  --output benchmark_suite/results/mac_m4_local_metadata.json \
  --summary-output benchmark_suite/results/mac_m4_local_metadata_summary.md \
  --compiler clang \
  --compiler /opt/homebrew/opt/llvm/bin/clang \
  --binary benchmark_suite/bin/membench
```

Review the manual fields before serious experiments: cache hierarchy, memory type/channels, power mode, thermal state, and background activity.
