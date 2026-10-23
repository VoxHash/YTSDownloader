"""Optional process nice / idle-I/O so Suite downloads yield to interactive apps."""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, Optional

from ytscore.native_bridge import BIN_PRIO, find_binary, run_argv_json


def apply_process_priority(
    *,
    pid: Optional[int] = None,
    nice: int = 0,
    idle_io: bool = False,
) -> Dict[str, Any]:
    """
    Lower CPU and/or disk priority for ``pid`` (default: current process).

    Prefers native ``yts-prio`` (C or Zig build). Falls back to Python
    ``os.nice`` / ``ionice`` CLI. Never raises — returns a status dict.
    """
    target = int(pid if pid is not None else os.getpid())
    result: Dict[str, Any] = {
        "ok": True,
        "pid": target,
        "nice": None,
        "ionice_idle": False,
        "via": "noop",
        "warnings": [],
    }
    if nice == 0 and not idle_io:
        return result

    binary = find_binary(BIN_PRIO)
    if binary:
        argv = ["--pid", str(target)]
        if nice:
            argv.extend(["--nice", str(int(nice))])
        if idle_io:
            argv.append("--ionice-idle")
        data = run_argv_json(binary, argv)
        if data and data.get("ok"):
            result["nice"] = data.get("nice")
            result["ionice_idle"] = bool(data.get("ionice_idle"))
            result["via"] = "native"
            warns = data.get("warnings") or []
            if isinstance(warns, list):
                result["warnings"] = [str(w) for w in warns]
            return result
        result["warnings"].append("native yts-prio failed; trying Python fallback")

    return _apply_python_fallback(target, nice=nice, idle_io=idle_io, base=result)


def _apply_python_fallback(
    target: int,
    *,
    nice: int,
    idle_io: bool,
    base: Dict[str, Any],
) -> Dict[str, Any]:
    base["via"] = "python"
    if nice and target == os.getpid():
        try:
            # os.nice adds to current nice; compute delta from getpriority when possible.
            try:
                current = os.getpriority(os.PRIO_PROCESS, target)
                delta = int(nice) - int(current)
            except (AttributeError, OSError):
                delta = int(nice)
            if delta != 0:
                os.nice(delta)
            base["nice"] = int(nice)
        except OSError as exc:
            base["warnings"].append(f"os.nice failed: {exc}")
    elif nice and target != os.getpid():
        try:
            subprocess.run(
                ["renice", "-n", str(int(nice)), "-p", str(target)],
                capture_output=True,
                timeout=5,
                check=False,
            )
            base["nice"] = int(nice)
        except (OSError, subprocess.SubprocessError) as exc:
            base["warnings"].append(f"renice failed: {exc}")

    if idle_io:
        try:
            proc = subprocess.run(
                ["ionice", "-c", "3", "-p", str(target)],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if proc.returncode == 0:
                base["ionice_idle"] = True
            else:
                base["warnings"].append("ionice failed")
        except (OSError, subprocess.SubprocessError) as exc:
            base["warnings"].append(f"ionice unavailable: {exc}")
    return base
