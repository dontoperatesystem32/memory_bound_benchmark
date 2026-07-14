# Cross-Machine Pilot Comparison

- Left input: `results/mac_m4_pilot_memory_sweep.csv`
- Right input: `results/intel_i5_12400f/intel_i5_12400f_pilot_memory_sweep.csv`
- Comparison CSV: `results/mac_m4_vs_intel_i5_12400f_pilot_comparison.csv`
- Machines: `mac_m4_local` and `intel_i5_12400f`
- Matched workload groups: 196
- Left-only groups: 0
- Right-only groups: 0
- CV warning threshold: 10.0%
- `mac_m4_local` groups above CV threshold: 11
- `intel_i5_12400f` groups above CV threshold: 0

This report compares matched normalized CSV outputs from the same benchmark configuration. The numbers should be read as workload-specific pilot measurements on two non-equivalent consumer systems, not as a general architecture ranking.

Bandwidth is the benchmark's effective useful data-movement rate. For strided traversal, this is useful payload bandwidth and does not attempt to count every cache-line byte fetched by the hardware.

## Large Working-Set Summary

| Workload | Array MiB | Threads | mac_m4_local GB/s | intel_i5_12400f GB/s | mac_m4_local/intel_i5_12400f | mac_m4_local speedup | intel_i5_12400f speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| sequential | 256.0 | 1 | 15.14 | 15.98 | 0.95 | 1.00 | 1.00 |
| reduction | 256.0 | 1 | 14.89 | 15.04 | 0.99 | 1.00 | 1.00 |
| reduction | 256.0 | 4 | 56.14 | 44.94 | 1.25 | 3.77 | 2.99 |
| triad | 256.0 | 1 | 92.54 | 29.11 | 3.18 | 1.00 | 1.00 |
| triad | 256.0 | 2 | 94.35 | 32.04 | 2.94 | 1.02 | 1.10 |
| triad | 256.0 | 4 | 94.09 | 42.54 | 2.21 | 1.02 | 1.46 |
| stencil1d | 256.0 | 1 | 167.13 | 47.56 | 3.51 | 1.00 | 1.00 |
| stencil1d | 256.0 | 4 | 195.83 | 73.68 | 2.66 | 1.17 | 1.55 |

## Triad One-Thread Working-Set Sweep

| Workload | Array MiB | Threads | mac_m4_local GB/s | intel_i5_12400f GB/s | mac_m4_local/intel_i5_12400f | mac_m4_local speedup | intel_i5_12400f speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| triad | 0.2 | 1 | 117.11 | 137.56 | 0.85 | 1.00 | 1.00 |
| triad | 1.0 | 1 | 119.53 | 63.53 | 1.88 | 1.00 | 1.00 |
| triad | 4.0 | 1 | 118.82 | 58.91 | 2.02 | 1.00 | 1.00 |
| triad | 8.0 | 1 | 115.62 | 38.35 | 3.01 | 1.00 | 1.00 |
| triad | 16.0 | 1 | 93.61 | 34.67 | 2.70 | 1.00 | 1.00 |
| triad | 64.0 | 1 | 92.43 | 29.65 | 3.12 | 1.00 | 1.00 |
| triad | 256.0 | 1 | 92.54 | 29.11 | 3.18 | 1.00 | 1.00 |

## Large Strided Traversal, One Thread

| Workload | Array MiB | Threads | mac_m4_local GB/s | intel_i5_12400f GB/s | mac_m4_local/intel_i5_12400f | mac_m4_local speedup | intel_i5_12400f speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| strided / stride 1 | 256.0 | 1 | 15.02 | 15.05 | 1.00 | 1.00 | 1.00 |
| strided / stride 2 | 256.0 | 1 | 14.54 | 10.97 | 1.32 | 1.00 | 1.00 |
| strided / stride 4 | 256.0 | 1 | 14.06 | 7.12 | 1.98 | 1.00 | 1.00 |
| strided / stride 8 | 256.0 | 1 | 8.58 | 3.69 | 2.33 | 1.00 | 1.00 |
| strided / stride 16 | 256.0 | 1 | 3.12 | 2.22 | 1.41 | 1.00 | 1.00 |
| strided / stride 32 | 256.0 | 1 | 2.79 | 1.84 | 1.52 | 1.00 | 1.00 |

## Large Strided Traversal, Four Threads

| Workload | Array MiB | Threads | mac_m4_local GB/s | intel_i5_12400f GB/s | mac_m4_local/intel_i5_12400f | mac_m4_local speedup | intel_i5_12400f speedup |
|---|---:|---:|---:|---:|---:|---:|---:|
| strided / stride 1 | 256.0 | 4 | 56.85 | 45.36 | 1.25 | 3.78 | 3.01 |
| strided / stride 2 | 256.0 | 4 | 36.91 | 23.94 | 1.54 | 2.54 | 2.18 |
| strided / stride 4 | 256.0 | 4 | 18.58 | 11.90 | 1.56 | 1.32 | 1.67 |
| strided / stride 8 | 256.0 | 4 | 9.29 | 5.94 | 1.56 | 1.08 | 1.61 |
| strided / stride 16 | 256.0 | 4 | 4.65 | 3.86 | 1.20 | 1.49 | 1.74 |
| strided / stride 32 | 256.0 | 4 | 4.37 | 3.39 | 1.29 | 1.57 | 1.85 |

## Initial Interpretation

- The two CSV files are directly comparable at the pipeline level: they contain the same 196 workload groups, generated from the same configuration and schema.
- `intel_i5_12400f` has no groups above the 10.0% CV threshold in this sweep; `mac_m4_local` has several higher-variation groups, mostly four-thread stencil or strided cases where macOS thread placement cannot be verified.
- The contiguous Triad measurements show the expected memory-bandwidth saturation behavior: adding threads improves throughput only until the memory path saturates for that workload.
- Strided traversal shows clear loss of useful bandwidth at larger strides, which is consistent with cache-line underutilization and poorer spatial locality.
- The local machines are still not controlled architecture equivalents. These results validate the measurement workflow and reveal workload-specific behavior, but they should not be framed as final ARM64-vs-x86-64 conclusions.

## Next Analysis Steps

- Add a compact figure set for the interim report using Triad scaling, large working-set stride sensitivity, and runtime versus working-set size.
- Decide whether to rerun the highest-variation Mac groups or simply report them as a limitation caused by scheduler and affinity constraints.
- Preserve raw CSV, metadata, summaries, and plots together for each machine so that the experiment can be reproduced later.
