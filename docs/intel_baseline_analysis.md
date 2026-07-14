# Intel Baseline Validation Analysis

## Validation Status

The Intel Core i5-12400F pipeline completed the initial custom validation matrix, official STREAM baseline, matching custom STREAM-style run, metadata capture, normalization, comparison report, and plotting workflow. The executable is a native x86-64 binary built with Clang 22.1.8 and dynamically linked to LLVM `libomp.so`.

Official STREAM used 20,000,000 elements per array, approximately 457.8 MiB across its three arrays, and ten executions per kernel. STREAM confirmed the requested 1, 2, and 4 OpenMP threads and validated its numerical solution for every run.

## STREAM Comparison

Custom Scale, Add, and Triad results closely follow official STREAM at every tested thread count. Best custom-to-official bandwidth ratios range from approximately 0.979 to 1.004 for these kernels. This supports the custom timing and normalization workflow without implying that the implementations are identical.

Custom Copy reaches approximately 63% and 66% of official STREAM at one and two threads, then approximately 94% at four threads. Repetition variation in the custom Copy measurements is low, so this is a repeatable implementation difference rather than obvious measurement noise. Possible causes include compiler optimization, alias analysis, and generated store behavior. The discrepancy should be investigated separately; official STREAM remains the recognized bandwidth baseline.

## Scaling And Variation

For the 192 MiB custom Triad traffic count, median bandwidth rises from approximately 28.75 GB/s at one thread to 32.58 GB/s at two threads and 41.65 GB/s at four threads. This is about 1.45 times the one-thread bandwidth at four threads, showing useful but sublinear scaling under memory pressure.

Large-working-set Triad measurements are stable, with coefficients of variation below approximately 1% at one and four threads. Several smaller cache-resident groups vary by more than 10%, and some exceed 20%, because individual timed regions are too short. The next sweep therefore batches multiple kernel calls per timed repetition and uses seven independent repetitions.

The initial strided traversal was serial even when the output rows requested multiple threads. Those rows are retained only as pipeline-development evidence and must not be used for OpenMP scaling conclusions. The kernel has been corrected before the next experiment campaign.

## Interpretation Boundary

These results validate the pipeline and establish a local Intel baseline. They do not establish general x86-64 performance, and comparison with the Mac must remain workload- and configuration-specific.
