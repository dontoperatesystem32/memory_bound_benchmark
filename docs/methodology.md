# Methodology Notes

## What Portable Means

Portable means that the benchmark workflow uses the same build/run interface, CSV schema, metadata collection, and plotting scripts across systems. It does not mean the hardware is treated as identical.

Interpretation must record machine-specific details such as CPU model, cache hierarchy, memory subsystem, operating system, compiler, OpenMP runtime, and power/thermal conditions.

## Cache Level Framing

This project studies cache behavior indirectly through working-set-size sweeps. It does not isolate only L1, L2, or last-level cache. Instead, array sizes are chosen so some runs are likely cache-resident and others exceed cache capacity and become main-memory-bound.

## Comparison Rules

Avoid general processor superiority claims. Valid comparisons are workload-specific:

- kernel
- working-set size
- thread count
- compiler and flags
- machine configuration
- metric being compared

Preferred architecture-neutral metrics include runtime, effective bandwidth, speedup, scaling efficiency, saturation point, working-set-size effects, and repeated-run variation.

