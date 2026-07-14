# Development Notes

This file records implementation decisions, setup findings, validation results, and limitations for the memory-bound benchmark pipeline. It is intended to support the interim and final reports.

## 2026-07-14

### Initial implementation pass started

- Action: Re-read the submitted proposal and professor/supervisor comments.
- Reason: Align the implementation with the approved project framing: portable methodology, memory-bound workloads, and workload-specific comparison rather than processor superiority claims.
- Result: First implementation scope set to a hybrid pipeline: established benchmark integrations plus custom kernels for controlled experiments and unified CSV output.
- Next step: Create the benchmark suite scaffold, buildable custom kernels, external benchmark integration notes, and scripts for running/plotting.

### Local toolchain inspection

- Action: Checked the local compiler.
- Result: `clang` is Apple Clang 21.0.0 targeting `arm64-apple-darwin25.5.0`. The `gcc` command on this Mac also resolves to Apple Clang in earlier checks. Homebrew LLVM was not present at `/opt/homebrew/opt/llvm` during planning.
- Decision: Keep LLVM/Clang as the preferred compiler family, but make the Makefile configurable. OpenMP is optional at build time so the project can compile before Homebrew LLVM/libomp is installed.
- Limitation: Apple Clang normally does not provide OpenMP support out of the box. Multi-threaded validation should use Homebrew LLVM/Clang with `libomp` when available.

### Benchmark suite scaffold created

- Action: Created `benchmark_suite/` with source, headers, scripts, configs, external benchmark notes, methodology docs, results, and plots directories.
- Reason: Establish a reproducible project structure before running larger experiments.
- Result: The tree now separates custom kernels, established benchmark integration notes, machine configs, generated results, generated plots, and methodology documentation.
- Next step: Keep adding established benchmark wrappers/parsers as they become useful, starting with official STREAM normalization.

### Custom memory-bound benchmark executable implemented

- Action: Implemented `benchmark_suite/bin/membench` from C sources under `benchmark_suite/src/`.
- Kernels included: `copy`, `scale`, `add`, `triad`, `sequential`, `strided`, `reduction`, and `stencil1d`.
- Output: CSV rows use the shared schema `source_benchmark,machine_id,kernel,elements,bytes,stride,threads,repetition,runtime_sec,bandwidth_gbps,checksum,compiler,compiler_flags`.
- Decision: Custom kernels are included for controlled experiments and unified CSV output, while established benchmarks such as STREAM remain first-class external integrations.
- Limitation: The first local build is serial because OpenMP is not configured yet.

### Established benchmark integration started

- Action: Added `benchmark_suite/external/README.md` and `benchmark_suite/scripts/normalize_stream.py`.
- Reason: The project should not reinvent established benchmarks unnecessarily. STREAM will serve as the recognized baseline for Copy, Scale, Add, and Triad behavior.
- Result: Official STREAM output can be normalized into the same CSV schema used by the custom kernels.
- Verification: Tested the normalizer with a representative STREAM-style output sample in `/tmp`; it emitted Copy, Scale, Add, and Triad rows using the shared schema.
- Next step: Download/build official STREAM separately, save raw output, and test the normalizer on real STREAM output.

### Serial local validation completed

- Action: Built the serial benchmark executable with the local Apple Clang toolchain.
- Result: `make -C benchmark_suite` completed successfully.
- Action: Ran a Triad smoke test and a serial validation matrix using `benchmark_suite/configs/mac_m4_serial_smoke.json`.
- Result: `benchmark_suite/results/mac_m4_serial_smoke.csv` contains 27 data rows plus the header for `triad`, `reduction`, and `strided` across three working-set sizes and three repetitions.
- Interpretation limitation: These are serial smoke-test results only. They validate the pipeline mechanics, not OpenMP scaling.

### OpenMP build checked

- Action: Ran `make -C benchmark_suite openmp` using the local default compiler.
- Result: Build failed with `clang: error: unsupported option '-fopenmp'`, confirming that Apple Clang cannot be used for OpenMP as configured.
- Decision: The executable now rejects `--threads` values greater than `1` when built without OpenMP. This avoids misleading CSV rows.
- Next step: Install/configure Homebrew LLVM and `libomp` before running multi-threaded experiments on macOS.

### Plotting pipeline validated without external Python dependencies

- Action: Implemented dependency-free SVG plotting in `benchmark_suite/scripts/plot_results.py`.
- Reason: `matplotlib` is not installed locally, and plotting should work without delaying the project on dependency setup.
- Result: SVG plots were generated under `benchmark_suite/plots/` for bandwidth vs. threads, runtime vs. size, and speedup vs. threads.
- Limitation: Current speedup/thread plots are not scientifically meaningful yet because the serial validation has only one thread. They confirm plot generation only.

### Metadata collection checked

- Action: Ran `benchmark_suite/scripts/collect_metadata.py` for `mac_m4_local`.
- Result: Basic platform/compiler metadata was written to `benchmark_suite/results/mac_m4_local_metadata.json`.
- Limitation: `sysctl` access is blocked in this sandbox, so CPU core count and memory size were marked unavailable. These fields should be completed manually before report use.

### Verification summary

- `make -C benchmark_suite` succeeds with the serial local compiler.
- Python scripts pass `py_compile`.
- Serial custom benchmark output, metadata capture, STREAM normalization, and SVG plotting have all been exercised.
- OpenMP remains the main environment setup blocker for valid multi-threaded experiments on macOS.

## 2026-07-14 Homebrew LLVM/OpenMP validation

### Homebrew LLVM/OpenMP validation completed

- Action: Rechecked Homebrew LLVM after installation.
- Result: `/opt/homebrew/opt/llvm/bin/clang --version` reports Homebrew Clang 22.1.8 targeting `arm64-apple-darwin25.5.0`.
- Action: Rebuilt the benchmark with `make -C benchmark_suite openmp CC=/opt/homebrew/opt/llvm/bin/clang`.
- Initial result: Build reached the OpenMP compiler and failed on `stencil1d` because the loop condition `i + 1 < elements` is not an OpenMP canonical loop form.
- Fix: Changed the stencil loop to `i < elements - 1`.
- Final result: OpenMP build succeeded with Homebrew Clang 22.1.8.

### OpenMP smoke and validation runs completed

- Action: Ran an OpenMP Triad smoke test with `--threads 4`.
- Result: `benchmark_suite/results/openmp_smoke.csv` contains valid rows and reports `clang 22.1.8`.
- Linkage check: `otool -L benchmark_suite/bin/membench` shows the executable links against `/opt/homebrew/opt/llvm/lib/libomp.dylib`.
- Action: Ran the configured OpenMP validation matrix with `benchmark_suite/configs/mac_m4_local.json`.
- Result: `benchmark_suite/results/mac_m4_openmp_validation.csv` contains 81 data rows plus the header for `triad`, `reduction`, and `strided` across three working-set sizes, thread counts 1/2/4, and three repetitions.
- Action: Regenerated SVG plots from the OpenMP validation CSV.
- Result: `benchmark_suite/plots/` now contains plots based on the multi-thread validation run.
- Interpretation limitation: This is still a small validation run, not a final experiment. Small working-set sizes show visible timing noise, so later runs should use larger sizes, more repetitions, and controlled background/power conditions.

## 2026-07-14 STREAM baseline integration

### Official STREAM source integrated

- Action: Downloaded official STREAM files from the University of Virginia STREAM source directory into `benchmark_suite/external/stream/`.
- Files: `stream.c`, `mysecond.c`, `LICENSE.txt`, and `READ.ME`.
- Source URL: `https://www.cs.virginia.edu/stream/FTP/Code/`.
- Decision: Treat official STREAM as the recognized baseline for Copy, Scale, Add, and Triad. Keep custom kernels for controlled experiments and unified pipeline behavior, not as a replacement for STREAM.

### STREAM build/run wrapper added

- Action: Added `benchmark_suite/scripts/run_stream_baseline.py`.
- Build command used internally: `/opt/homebrew/opt/llvm/bin/clang -O3 -fopenmp -DSTREAM_ARRAY_SIZE=20000000 -DNTIMES=10 benchmark_suite/external/stream/stream.c -o benchmark_suite/external/stream/build/stream_20000000_10`.
- Compiler: Homebrew Clang 22.1.8.
- Array size: 20,000,000 elements per array, approximately 152.6 MiB per STREAM array and 457.8 MiB total.
- Thread counts: 1, 2, and 4 via `OMP_NUM_THREADS`.
- Note: `stream.c` already defines `mysecond`, so linking `mysecond.c` separately caused a duplicate-symbol error. The wrapper compiles `stream.c` alone and keeps `mysecond.c` as an official downloaded support/reference file.

### Official STREAM output normalized

- Action: Ran official STREAM for thread counts 1, 2, and 4.
- Raw outputs:
  - `benchmark_suite/results/raw_stream_mac_m4_local_threads_1.txt`
  - `benchmark_suite/results/raw_stream_mac_m4_local_threads_2.txt`
  - `benchmark_suite/results/raw_stream_mac_m4_local_threads_4.txt`
- Normalized output: `benchmark_suite/results/stream_mac_m4_normalized.csv`.
- Result: Normalized CSV has 12 data rows plus header for Copy, Scale, Add, and Triad across three thread counts.
- Parser correction: `normalize_stream.py` now records STREAM's minimum time field for the `runtime_sec` value because STREAM reports best bandwidth from minimum time.

### Custom STREAM-style comparison generated

- Action: Added `benchmark_suite/configs/mac_m4_custom_stream_compare.json` and ran custom Copy, Scale, Add, and Triad kernels with 20,000,000 elements, thread counts 1/2/4, and 3 repetitions.
- Output: `benchmark_suite/results/custom_stream_mac_m4_compare.csv`, containing 36 data rows plus header.
- Methodology fix: Custom output-array kernels originally included checksum work inside the timed interval. This was corrected so checksums are computed after timing for Copy, Scale, Add, Triad, and Stencil1D.
- Comparison helper: Added `benchmark_suite/scripts/compare_stream_custom.py`.
- Comparison output: `benchmark_suite/results/stream_vs_custom_mac_m4.md`.
- Observation: Best-observed custom STREAM-style bandwidth is broadly in the same range as official STREAM, especially for Scale/Add/Triad, while differences remain expected because the implementations and reporting conventions are not identical.

### STREAM plots generated

- Action: Generated SVG plots from official STREAM normalized output and custom STREAM-style comparison output.
- Official STREAM plots: `benchmark_suite/plots/stream/`.
- Custom comparison plots: `benchmark_suite/plots/custom_stream_compare/`.
- Interpretation limitation: These plots are useful for validating the pipeline and comparing trends, but they are still a Mac-only baseline and should not be treated as a final architecture comparison.

## 2026-07-14 metadata completeness improvement

### Metadata collector expanded

- Action: Reworked `benchmark_suite/scripts/collect_metadata.py` to produce a richer machine metadata record.
- Automatic fields now include OS version, Darwin kernel string, model name, model identifier, chip name, core configuration, memory size, Apple Clang version, Homebrew Clang version, benchmark binary path, dynamic library linkage, and whether `libomp` is detected.
- Privacy decision: Sensitive identifiers from `system_profiler`, including serial number, hardware UUID, and provisioning UDID, are redacted by default.
- Limitation: `sysctl` remains blocked in this sandbox, so those fields are recorded as unavailable with the associated error message.

### Mac metadata regenerated

- Action: Regenerated `benchmark_suite/results/mac_m4_local_metadata.json`.
- Action: Added human-readable summary output at `benchmark_suite/results/mac_m4_local_metadata_summary.md`.
- Result: Metadata now records MacBook Air `Mac16,12`, Apple M4, 10 cores with 4 performance and 6 efficiency cores, 16 GB memory, macOS 26.5.2 build 25F84, Apple Clang 21.0.0, Homebrew Clang 22.1.8, and detected Homebrew `libomp` linkage for `benchmark_suite/bin/membench`.
- Manual review still required: cache hierarchy, memory type/channels, power mode, thermal conditions, and background activity before serious experiments.

## 2026-07-14 Linux portability fix

### `posix_memalign` declaration fixed for strict C builds

- Context: The Intel x86-64 CachyOS build with `clang -std=c11` failed because `posix_memalign` was not declared.
- Cause: On glibc/Linux, `posix_memalign` is hidden in strict C modes unless an appropriate POSIX feature-test macro is defined before system headers.
- Fix: Added `_POSIX_C_SOURCE 200112L` before includes in `src/main.c`.
- Verification: Rebuilt successfully on macOS with Homebrew Clang/OpenMP after the change.
- Next step: Pull/sync this fix on the CachyOS machine and rebuild with `make -C memory_bound_benchmark openmp CC=clang`.
