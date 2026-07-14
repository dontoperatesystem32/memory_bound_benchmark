# Official STREAM vs Custom STREAM-Style Kernels

Bandwidth values are best observed values over available rows in GB/s. This matches STREAM's convention of reporting best bandwidth after repeated runs. Differences are descriptive only; official STREAM and the custom kernels are not claimed to be identical implementations.

| Kernel | Threads | STREAM GB/s | Custom GB/s | Custom/STREAM |
|---|---:|---:|---:|---:|
| copy | 1 | 92.968 | 79.365 | 0.854 |
| copy | 2 | 104.507 | 94.479 | 0.904 |
| copy | 4 | 103.531 | 89.837 | 0.868 |
| scale | 1 | 90.933 | 86.160 | 0.948 |
| scale | 2 | 96.386 | 98.705 | 1.024 |
| scale | 4 | 101.557 | 94.256 | 0.928 |
| add | 1 | 94.157 | 88.708 | 0.942 |
| add | 2 | 96.522 | 89.004 | 0.922 |
| add | 4 | 96.250 | 90.652 | 0.942 |
| triad | 1 | 93.894 | 88.561 | 0.943 |
| triad | 2 | 97.561 | 90.617 | 0.929 |
| triad | 4 | 97.189 | 93.989 | 0.967 |
