# Cross-Machine Pipeline Gate Analysis

## Gate Outcome

Both the Apple M4 and Intel Core i5-12400F completed the 54-row schema-v2 gate. Each dataset contains the same kernels, element counts, strides, thread counts, warm-up count, timed iteration counts, compiler family, compiler flags, and normalized columns. Separate plots were generated for Triad, contiguous traversal, and stride-16 traversal.

Checksums are stable across repetitions and thread counts. Maximum relative checksum spread is below approximately \(10^{-12}\), consistent with floating-point reduction-order differences rather than a correctness failure.

## Intel Behavior

Intel measurements are generally stable. Triad coefficients of variation are below 2.5%, and contiguous traversal groups are below 3%. The large stride-16/four-thread group reaches 15.7% variation; the full sweep addresses this with four times more timed work and seven repetitions.

For the larger 8,388,608-element case, median Intel Triad bandwidth rises from approximately 29.50 GB/s at one thread to 33.25 GB/s at two threads and 43.86 GB/s at four threads. Contiguous traversal scales from approximately 15.00 GB/s to 47.57 GB/s, while stride-16 useful bandwidth scales from approximately 2.31 GB/s to 4.28 GB/s.

## Mac Behavior

The Mac produces coherent medians but greater variation in several smaller groups. Homebrew `libomp` reports processor affinity as undefined on macOS, so exact placement across performance and efficiency cores cannot be controlled or verified in the same way as on Linux. Larger contiguous groups are substantially more stable than small/cache-resident groups.

For the larger case, median Mac Triad bandwidth is approximately 91.02 GB/s at one thread and 96.91 GB/s at four threads, indicating early bandwidth saturation. Contiguous traversal scales from approximately 16.28 GB/s to 57.75 GB/s, while stride-16 useful bandwidth scales from approximately 2.98 GB/s to 5.30 GB/s.

## Decision

The gate passes for correctness, schema consistency, portability, and basic scaling behavior. The full pilot sweep is approved with seven repetitions, longer timed batches, deterministic job shuffling, and variation reporting. Results remain workload-specific and do not support general processor-superiority claims.
