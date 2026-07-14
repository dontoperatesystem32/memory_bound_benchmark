# Machine Metadata Summary

- Machine ID: `mac_m4_local`
- Collected UTC: `2026-07-14T01:50:43.189480+00:00`
- Model: MacBook Air (Mac16,12)
- Chip: Apple M4
- Cores: 10 (4 Performance and 6 Efficiency)
- Memory: 16 GB
- OS: macOS 26.5.2 build 25F84
- Benchmark binary: `benchmark_suite/bin/membench`
- OpenMP runtime detected: True

## Compilers

- `clang`: Apple clang version 21.0.0 (clang-2100.1.1.101)
- `/opt/homebrew/opt/llvm/bin/clang`: Homebrew clang version 22.1.8

## Manual Review Required

- cache_hierarchy: Fill from reliable vendor/system documentation if needed for analysis.
- memory_type_and_channels: Fill manually if available; macOS system_profiler does not provide enough detail.
- power_mode: Record manually before each serious run, e.g. plugged in/battery, Low Power Mode off/on.
- thermal_conditions: Record manually before each serious run, e.g. cool start, background apps minimized.
- run_environment: Record terminal/session details and whether the machine was idle.

## Interpretation Note

Metadata supports workload-specific interpretation only. It must not be used to claim general processor superiority across architectures.
