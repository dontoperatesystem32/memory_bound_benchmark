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
import os
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
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            env=environment,
        )
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


def parse_colon_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def linux_os_release() -> dict[str, str]:
    try:
        return dict(platform.freedesktop_os_release())
    except (AttributeError, OSError):
        return {}


def linux_memory() -> tuple[str, int | None]:
    try:
        fields = parse_colon_fields(Path("/proc/meminfo").read_text(encoding="utf-8"))
    except OSError:
        return "unavailable", None
    match = re.match(r"^(\d+)\s+kB$", fields.get("MemTotal", ""), re.I)
    if not match:
        return "unavailable", None
    memory_bytes = int(match.group(1)) * 1024
    return f"{memory_bytes / 1024**3:.2f} GiB", memory_bytes


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
    linkage = None
    linkage_tool = None
    if exists and platform.system() == "Darwin":
        linkage = run(["otool", "-L", str(path)])
        linkage_tool = "otool -L"
    elif exists and platform.system() == "Linux":
        linkage = run(["ldd", str(path)])
        linkage_tool = "ldd"
    linkage_text = linkage["stdout"] if linkage and linkage["available"] else ""
    runtime_names = sorted(set(re.findall(r"\blib(?:g)?omp(?:\.[^\s=]+)?", linkage_text)))
    return {
        "path": str(path),
        "available": exists,
        "linkage_tool": linkage_tool,
        "dynamic_libraries": linkage_text.splitlines(),
        "openmp_runtime_detected": bool(runtime_names),
        "openmp_runtimes": runtime_names,
        "linkage_error": linkage["stderr"] if linkage and not linkage["available"] else "",
    }


def write_markdown_summary(path: Path, metadata: dict[str, Any]) -> None:
    hardware = metadata["hardware"]
    os_metadata = metadata["os"]
    sw_vers = os_metadata["sw_vers"]
    os_release = os_metadata.get("os_release", {})
    compilers = metadata["compilers"]
    binary = metadata["benchmark_binary"]

    if sw_vers:
        os_description = (
            f"{sw_vers.get('ProductName', 'unavailable')} "
            f"{sw_vers.get('ProductVersion', 'unavailable')} "
            f"build {sw_vers.get('BuildVersion', 'unavailable')}"
        )
    elif os_release:
        os_description = os_release.get("PRETTY_NAME", os_release.get("NAME", "Linux"))
    else:
        os_description = platform.system() or "unavailable"

    runtime_description = ", ".join(binary.get("openmp_runtimes", [])) or "none detected"

    lines = [
        "# Machine Metadata Summary",
        "",
        f"- Machine ID: `{metadata['machine_id']}`",
        f"- Collected UTC: `{metadata['collected_at_utc']}`",
        f"- Model: {hardware['model_name']} ({hardware['model_identifier']})",
        f"- Chip: {hardware['chip']}",
        f"- Cores: {hardware['total_cores']}",
        f"- Memory: {hardware['memory']}",
        f"- OS: {os_description}",
        f"- Benchmark binary: `{binary['path']}`",
        f"- OpenMP runtime: {runtime_description}",
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
    system = platform.system()
    sw_vers = run(["sw_vers"]) if system == "Darwin" else {"available": False, "stdout": ""}
    uname = run(["uname", "-a"])
    profiler = run(["system_profiler", "SPHardwareDataType"]) if system == "Darwin" else {"available": False, "stdout": ""}
    lscpu = run(["lscpu"]) if system == "Linux" else {"available": False, "stdout": ""}
    os_release = linux_os_release() if system == "Linux" else {}
    sysctl_queries = {}
    if system == "Darwin":
        sysctl_queries = {
            "machdep.cpu.brand_string": run(["sysctl", "-n", "machdep.cpu.brand_string"]),
            "hw.physicalcpu": run(["sysctl", "-n", "hw.physicalcpu"]),
            "hw.logicalcpu": run(["sysctl", "-n", "hw.logicalcpu"]),
            "hw.memsize": run(["sysctl", "-n", "hw.memsize"]),
        }

    profiler_hardware = (
        parse_system_profiler_hardware(profiler["stdout"], args.include_sensitive)
        if profiler["available"]
        else {}
    )
    lscpu_fields = parse_colon_fields(lscpu["stdout"]) if lscpu["available"] else {}
    if system == "Linux":
        memory, memory_bytes = linux_memory()
        hardware_source = "lscpu and /proc/meminfo"
        hardware_fields = lscpu_fields
        model_name = lscpu_fields.get("Model name", "unavailable")
        model_identifier = f"family {lscpu_fields.get('CPU family', '?')}, model {lscpu_fields.get('Model', '?')}"
        chip = model_name
        total_cores = lscpu_fields.get("Core(s) per socket", "unavailable")
    else:
        memory = profiler_hardware.get("Memory", "unavailable")
        memory_bytes = parse_memory_bytes(memory)
        hardware_source = "system_profiler SPHardwareDataType"
        hardware_fields = profiler_hardware
        model_name = profiler_hardware.get("Model Name", "unavailable")
        model_identifier = profiler_hardware.get("Model Identifier", "unavailable")
        chip = profiler_hardware.get("Chip", "unavailable")
        total_cores = profiler_hardware.get("Total Number of Cores", "unavailable")

    metadata = {
        "schema_version": 3,
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
            "system": system,
            "sw_vers": parse_sw_vers(sw_vers["stdout"]) if sw_vers["available"] else {},
            "os_release": os_release,
            "uname": uname["stdout"] if uname["available"] else "unavailable",
        },
        "hardware": {
            "source": hardware_source,
            "fields": hardware_fields,
            "model_name": model_name,
            "model_identifier": model_identifier,
            "chip": chip,
            "total_cores": total_cores,
            "logical_cpus": lscpu_fields.get("CPU(s)", "unavailable"),
            "threads_per_core": lscpu_fields.get("Thread(s) per core", "unavailable"),
            "sockets": lscpu_fields.get("Socket(s)", "unavailable"),
            "architecture": lscpu_fields.get("Architecture", platform.machine()),
            "cache_hierarchy": {
                canonical: lscpu_fields[source_key]
                for canonical, source_key in {
                    "L1d": "L1d cache",
                    "L1i": "L1i cache",
                    "L2": "L2 cache",
                    "L3": "L3 cache",
                }.items()
                if source_key in lscpu_fields
            },
            "numa": {
                key: value
                for key, value in lscpu_fields.items()
                if key.startswith("NUMA node")
            },
            "memory": memory,
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
            "cache_hierarchy": "Verify automatically reported cache values against reliable system or vendor documentation.",
            "memory_type_and_channels": "Fill manually if available; standard OS tools may not report reliable type/channel details.",
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
