#!/usr/bin/env python3
"""Collect machine metadata for benchmark interpretation.

The collector is intentionally best-effort. Some macOS hardware queries are
blocked in sandboxed environments, so the output records unavailable fields
instead of silently omitting them. Sensitive identifiers from system_profiler
are redacted by default.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SENSITIVE_HARDWARE_KEYS = {
    "Serial Number (system)",
    "Hardware UUID",
    "Provisioning UDID",
}


def run(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, check=False, text=True, capture_output=True)
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "available": completed.returncode == 0 and bool(completed.stdout.strip()),
        }
    except OSError as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "available": False,
        }


def first_line(text: str) -> str:
    return text.splitlines()[0] if text else "unavailable"


def parse_system_profiler_hardware(text: str, include_sensitive: bool) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if ": " not in stripped:
            continue
        key, value = stripped.split(": ", 1)
        if key in SENSITIVE_HARDWARE_KEYS and not include_sensitive:
            fields[key] = "redacted"
        else:
            fields[key] = value
    return fields


def parse_sw_vers(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def parse_memory_bytes(memory_text: str) -> int | None:
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(GB|MB|GiB|MiB)$", memory_text.strip(), re.I)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit in {"gb", "gib"}:
        return int(value * 1024**3)
    if unit in {"mb", "mib"}:
        return int(value * 1024**2)
    return None


def compiler_record(path: str) -> dict[str, Any]:
    version = run([path, "--version"])
    return {
        "path": path,
        "available": version["available"],
        "version_first_line": first_line(version["stdout"]),
        "version_full": version["stdout"] if version["available"] else "unavailable",
        "error": version["stderr"] if not version["available"] else "",
    }


def binary_record(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"path": None, "available": False}
    exists = path.exists()
    linkage = run(["otool", "-L", str(path)]) if exists and platform.system() == "Darwin" else None
    return {
        "path": str(path),
        "available": exists,
        "dynamic_libraries": linkage["stdout"].splitlines() if linkage and linkage["available"] else [],
        "openmp_runtime_detected": bool(linkage and "libomp" in linkage["stdout"]),
    }


def write_markdown_summary(path: Path, metadata: dict[str, Any]) -> None:
    hardware = metadata["hardware"]
    os_info = metadata["os"]["sw_vers"]
    compilers = metadata["compilers"]
    binary = metadata["benchmark_binary"]

    lines = [
        "# Machine Metadata Summary",
        "",
        f"- Machine ID: `{metadata['machine_id']}`",
        f"- Collected UTC: `{metadata['collected_at_utc']}`",
        f"- Model: {hardware['model_name']} ({hardware['model_identifier']})",
        f"- Chip: {hardware['chip']}",
        f"- Cores: {hardware['total_cores']}",
        f"- Memory: {hardware['memory']}",
        f"- OS: {os_info.get('ProductName', 'unavailable')} {os_info.get('ProductVersion', 'unavailable')} build {os_info.get('BuildVersion', 'unavailable')}",
        f"- Benchmark binary: `{binary['path']}`",
        f"- OpenMP runtime detected: {binary['openmp_runtime_detected']}",
        "",
        "## Compilers",
        "",
    ]
    for compiler in compilers:
        lines.append(f"- `{compiler['path']}`: {compiler['version_first_line']}")
    lines.extend(
        [
            "",
            "## Manual Review Required",
            "",
        ]
    )
    for key, value in metadata["manual_review_required"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Interpretation Note",
            "",
            metadata["interpretation_note"],
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--machine-id", required=True)
    parser.add_argument(
        "--compiler",
        action="append",
        default=[],
        help="Compiler path to record. Can be passed multiple times.",
    )
    parser.add_argument("--binary", type=Path, default=Path("benchmark_suite/bin/membench"))
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--include-sensitive", action="store_true")
    args = parser.parse_args()

    compiler_paths = args.compiler or ["clang", "/opt/homebrew/opt/llvm/bin/clang"]
    sw_vers = run(["sw_vers"])
    uname = run(["uname", "-a"])
    profiler = run(["system_profiler", "SPHardwareDataType"])
    sysctl_queries = {
        "machdep.cpu.brand_string": run(["sysctl", "-n", "machdep.cpu.brand_string"]),
        "hw.physicalcpu": run(["sysctl", "-n", "hw.physicalcpu"]),
        "hw.logicalcpu": run(["sysctl", "-n", "hw.logicalcpu"]),
        "hw.memsize": run(["sysctl", "-n", "hw.memsize"]),
    }

    hardware = parse_system_profiler_hardware(profiler["stdout"], args.include_sensitive) if profiler["available"] else {}
    memory_bytes = parse_memory_bytes(hardware.get("Memory", ""))

    metadata = {
        "schema_version": 2,
        "machine_id": args.machine_id,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "os": {
            "sw_vers": parse_sw_vers(sw_vers["stdout"]) if sw_vers["available"] else {},
            "uname": uname["stdout"] if uname["available"] else "unavailable",
        },
        "hardware": {
            "source": "system_profiler SPHardwareDataType",
            "fields": hardware,
            "model_name": hardware.get("Model Name", "unavailable"),
            "model_identifier": hardware.get("Model Identifier", "unavailable"),
            "chip": hardware.get("Chip", "unavailable"),
            "total_cores": hardware.get("Total Number of Cores", "unavailable"),
            "memory": hardware.get("Memory", "unavailable"),
            "memory_bytes_estimated": memory_bytes,
        },
        "sysctl": {
            key: {
                "available": value["available"],
                "value": value["stdout"] if value["available"] else "unavailable",
                "error": value["stderr"] if not value["available"] else "",
            }
            for key, value in sysctl_queries.items()
        },
        "compilers": [compiler_record(path) for path in compiler_paths],
        "benchmark_binary": binary_record(args.binary),
        "manual_review_required": {
            "cache_hierarchy": "Fill from reliable vendor/system documentation if needed for analysis.",
            "memory_type_and_channels": "Fill manually if available; macOS system_profiler does not provide enough detail.",
            "power_mode": "Record manually before each serious run, e.g. plugged in/battery, Low Power Mode off/on.",
            "thermal_conditions": "Record manually before each serious run, e.g. cool start, background apps minimized.",
            "run_environment": "Record terminal/session details and whether the machine was idle.",
        },
        "interpretation_note": (
            "Metadata supports workload-specific interpretation only. It must not be used to claim "
            "general processor superiority across architectures."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        f.write("\n")
    if args.summary_output is not None:
        write_markdown_summary(args.summary_output, metadata)
    print(f"Wrote {args.output}")
    if args.summary_output is not None:
        print(f"Wrote {args.summary_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
