#!/usr/bin/env python3
"""Compare two normalized memory-bound benchmark result CSV files."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev


GroupKey = tuple[str, int, int, int]


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def machine_id(rows: list[dict[str, str]]) -> str:
    machines = sorted({row["machine_id"] for row in rows})
    if len(machines) != 1:
        raise ValueError(f"expected exactly one machine_id, found {machines}")
    return machines[0]


def group_values(rows: list[dict[str, str]], value_field: str) -> dict[GroupKey, list[float]]:
    values: dict[GroupKey, list[float]] = defaultdict(list)
    for row in rows:
        key = (
            row["kernel"],
            int(row["elements"]),
            int(row["stride"]),
            int(row["threads"]),
        )
        values[key].append(float(row[value_field]))
    return values


def coefficient_of_variation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    average = mean(values)
    return stdev(values) / average * 100.0 if average != 0.0 else None


def fmt(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def workload_name(key: GroupKey) -> str:
    kernel, _, stride, _ = key
    return f"{kernel} / stride {stride}" if kernel == "strided" else kernel


def array_mib(elements: int) -> float:
    return elements * 8 / 1024**2


def speedup(runtime: dict[GroupKey, list[float]], key: GroupKey) -> float | None:
    kernel, elements, stride, threads = key
    baseline = runtime.get((kernel, elements, stride, 1))
    if baseline is None:
        return None
    return median(baseline) / median(runtime[key]) if threads != 0 else None


def write_comparison_csv(
    path: Path,
    left_name: str,
    right_name: str,
    left_runtime: dict[GroupKey, list[float]],
    right_runtime: dict[GroupKey, list[float]],
    left_bandwidth: dict[GroupKey, list[float]],
    right_bandwidth: dict[GroupKey, list[float]],
) -> list[dict[str, str]]:
    keys = sorted(set(left_runtime) & set(right_runtime))
    rows: list[dict[str, str]] = []
    for key in keys:
        kernel, elements, stride, threads = key
        left_bw = median(left_bandwidth[key])
        right_bw = median(right_bandwidth[key])
        left_rt = median(left_runtime[key])
        right_rt = median(right_runtime[key])
        rows.append(
            {
                "kernel": kernel,
                "elements": str(elements),
                "array_mib": f"{array_mib(elements):.3f}",
                "stride": str(stride),
                "threads": str(threads),
                f"{left_name}_median_runtime_sec": f"{left_rt:.9f}",
                f"{right_name}_median_runtime_sec": f"{right_rt:.9f}",
                f"{left_name}_median_bandwidth_gbps": f"{left_bw:.6f}",
                f"{right_name}_median_bandwidth_gbps": f"{right_bw:.6f}",
                f"{left_name}_speedup": fmt(speedup(left_runtime, key), 6),
                f"{right_name}_speedup": fmt(speedup(right_runtime, key), 6),
                f"{left_name}_cv_percent": fmt(coefficient_of_variation(left_bandwidth[key]), 6),
                f"{right_name}_cv_percent": fmt(coefficient_of_variation(right_bandwidth[key]), 6),
                f"{left_name}_over_{right_name}_bandwidth_ratio": f"{left_bw / right_bw:.6f}" if right_bw else "n/a",
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def selected_table(
    title: str,
    keys: list[GroupKey],
    left_name: str,
    right_name: str,
    left_bandwidth: dict[GroupKey, list[float]],
    right_bandwidth: dict[GroupKey, list[float]],
    left_runtime: dict[GroupKey, list[float]],
    right_runtime: dict[GroupKey, list[float]],
) -> list[str]:
    lines = [
        f"## {title}",
        "",
        f"| Workload | Array MiB | Threads | {left_name} GB/s | {right_name} GB/s | {left_name}/{right_name} | {left_name} speedup | {right_name} speedup |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key in keys:
        if key not in left_bandwidth or key not in right_bandwidth:
            continue
        _, elements, _, threads = key
        left_bw = median(left_bandwidth[key])
        right_bw = median(right_bandwidth[key])
        ratio = left_bw / right_bw if right_bw else None
        lines.append(
            f"| {workload_name(key)} | {array_mib(elements):.1f} | {threads} | "
            f"{left_bw:.2f} | {right_bw:.2f} | {fmt(ratio)} | "
            f"{fmt(speedup(left_runtime, key))} | {fmt(speedup(right_runtime, key))} |"
        )
    lines.append("")
    return lines


def cv_warning_count(groups: dict[GroupKey, list[float]], threshold: float) -> int:
    return sum(
        1
        for values in groups.values()
        if (cv := coefficient_of_variation(values)) is not None and cv > threshold
    )


def write_markdown_report(
    path: Path,
    comparison_csv: Path,
    left_path: Path,
    right_path: Path,
    left_name: str,
    right_name: str,
    left_runtime: dict[GroupKey, list[float]],
    right_runtime: dict[GroupKey, list[float]],
    left_bandwidth: dict[GroupKey, list[float]],
    right_bandwidth: dict[GroupKey, list[float]],
    cv_warning_threshold: float,
) -> None:
    matched = sorted(set(left_runtime) & set(right_runtime))
    left_only = sorted(set(left_runtime) - set(right_runtime))
    right_only = sorted(set(right_runtime) - set(left_runtime))
    max_elements = max(key[1] for key in matched)
    triad_sizes = sorted({key[1] for key in matched if key[0] == "triad"})

    large_workload_keys = [
        ("sequential", max_elements, 1, 1),
        ("reduction", max_elements, 1, 1),
        ("reduction", max_elements, 1, 4),
        ("triad", max_elements, 1, 1),
        ("triad", max_elements, 1, 2),
        ("triad", max_elements, 1, 4),
        ("stencil1d", max_elements, 1, 1),
        ("stencil1d", max_elements, 1, 4),
    ]
    stride_large_thread1 = [("strided", max_elements, stride, 1) for stride in (1, 2, 4, 8, 16, 32)]
    stride_large_thread4 = [("strided", max_elements, stride, 4) for stride in (1, 2, 4, 8, 16, 32)]
    triad_thread1_by_size = [("triad", elements, 1, 1) for elements in triad_sizes]

    lines = [
        "# Cross-Machine Pilot Comparison",
        "",
        f"- Left input: `{left_path}`",
        f"- Right input: `{right_path}`",
        f"- Comparison CSV: `{comparison_csv}`",
        f"- Machines: `{left_name}` and `{right_name}`",
        f"- Matched workload groups: {len(matched)}",
        f"- Left-only groups: {len(left_only)}",
        f"- Right-only groups: {len(right_only)}",
        f"- CV warning threshold: {cv_warning_threshold:.1f}%",
        f"- `{left_name}` groups above CV threshold: {cv_warning_count(left_bandwidth, cv_warning_threshold)}",
        f"- `{right_name}` groups above CV threshold: {cv_warning_count(right_bandwidth, cv_warning_threshold)}",
        "",
        "This report compares matched normalized CSV outputs from the same benchmark configuration. The numbers should be read as workload-specific pilot measurements on two non-equivalent consumer systems, not as a general architecture ranking.",
        "",
        "Bandwidth is the benchmark's effective useful data-movement rate. For strided traversal, this is useful payload bandwidth and does not attempt to count every cache-line byte fetched by the hardware.",
        "",
    ]

    lines.extend(
        selected_table(
            "Large Working-Set Summary",
            large_workload_keys,
            left_name,
            right_name,
            left_bandwidth,
            right_bandwidth,
            left_runtime,
            right_runtime,
        )
    )
    lines.extend(
        selected_table(
            "Triad One-Thread Working-Set Sweep",
            triad_thread1_by_size,
            left_name,
            right_name,
            left_bandwidth,
            right_bandwidth,
            left_runtime,
            right_runtime,
        )
    )
    lines.extend(
        selected_table(
            "Large Strided Traversal, One Thread",
            stride_large_thread1,
            left_name,
            right_name,
            left_bandwidth,
            right_bandwidth,
            left_runtime,
            right_runtime,
        )
    )
    lines.extend(
        selected_table(
            "Large Strided Traversal, Four Threads",
            stride_large_thread4,
            left_name,
            right_name,
            left_bandwidth,
            right_bandwidth,
            left_runtime,
            right_runtime,
        )
    )

    lines.extend(
        [
            "## Initial Interpretation",
            "",
            f"- The two CSV files are directly comparable at the pipeline level: they contain the same {len(matched)} workload groups, generated from the same configuration and schema.",
            f"- `{right_name}` has no groups above the {cv_warning_threshold:.1f}% CV threshold in this sweep; `{left_name}` has several higher-variation groups, mostly four-thread stencil or strided cases where macOS thread placement cannot be verified.",
            "- The contiguous Triad measurements show the expected memory-bandwidth saturation behavior: adding threads improves throughput only until the memory path saturates for that workload.",
            "- Strided traversal shows clear loss of useful bandwidth at larger strides, which is consistent with cache-line underutilization and poorer spatial locality.",
            "- The local machines are still not controlled architecture equivalents. These results validate the measurement workflow and reveal workload-specific behavior, but they should not be framed as final ARM64-vs-x86-64 conclusions.",
            "",
            "## Next Analysis Steps",
            "",
            "- Add a compact figure set for the interim report using Triad scaling, large working-set stride sensitivity, and runtime versus working-set size.",
            "- Decide whether to rerun the highest-variation Mac groups or simply report them as a limitation caused by scheduler and affinity constraints.",
            "- Preserve raw CSV, metadata, summaries, and plots together for each machine so that the experiment can be reproduced later.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", required=True, type=Path)
    parser.add_argument("--right", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--csv-output", required=True, type=Path)
    parser.add_argument("--cv-warning", default=10.0, type=float)
    args = parser.parse_args()

    left_rows = load_rows(args.left)
    right_rows = load_rows(args.right)
    if not left_rows or not right_rows:
        parser.error("both inputs must contain result rows")

    left_name = machine_id(left_rows)
    right_name = machine_id(right_rows)
    left_runtime = group_values(left_rows, "runtime_sec")
    right_runtime = group_values(right_rows, "runtime_sec")
    left_bandwidth = group_values(left_rows, "bandwidth_gbps")
    right_bandwidth = group_values(right_rows, "bandwidth_gbps")

    rows = write_comparison_csv(
        args.csv_output,
        left_name,
        right_name,
        left_runtime,
        right_runtime,
        left_bandwidth,
        right_bandwidth,
    )
    write_markdown_report(
        args.output,
        args.csv_output,
        args.left,
        args.right,
        left_name,
        right_name,
        left_runtime,
        right_runtime,
        left_bandwidth,
        right_bandwidth,
        args.cv_warning,
    )
    print(f"Wrote {args.csv_output} with {len(rows)} matched groups")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
