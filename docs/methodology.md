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

## Timing And Repetition

Each CSV row represents one independent repetition. Array initialization and the number of kernel calls recorded in `warmups` occur before the timed region. The `iterations` field records how many kernel calls are batched inside that timed region; `bytes` is the total useful byte count across the batch. Warm-up calls reduce first-use effects, while batching keeps cache-resident measurements long enough to reduce timer and OpenMP-launch overhead without changing the working set.

Summaries and plots use the median across independent repetitions. Reports should also include variation, preferably the coefficient of variation or an interquartile range. Very short measurements and groups with high variation must be treated as diagnostic rather than conclusive.

The full pilot configuration uses a recorded fixed seed to shuffle kernel/size/thread jobs. Both machines therefore execute the same reproducible order, while heat, background activity, and frequency changes are less likely to affect one contiguous workload family exclusively.

On macOS, Homebrew `libomp` accepts OpenMP affinity settings but reports processor affinity as undefined. Thread placement therefore cannot be controlled or verified in the same way as on Linux. This limitation is recorded explicitly, and Mac results rely on warm-ups, repeated runs, medians, and variation reporting rather than claims of identical core placement.

## Strided Access

Strided traversal reports useful bandwidth from the bytes explicitly loaded by the kernel. It does not claim that this equals physical memory-bus traffic: cache-line fetches can move substantially more data than the useful-byte count, especially at large strides. Stride results are therefore interpreted as access-efficiency trends, not as direct peak-bandwidth measurements.
