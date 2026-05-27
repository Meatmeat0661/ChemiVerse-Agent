"""Nautilus / Westlake 运行环境检测."""

from __future__ import annotations

import subprocess
import sys


def resolve_python(configured: str) -> str:
    """与启动 Streamlit 的 Python 一致，避免 `python` 指向错误版本。"""
    configured = (configured or "").strip()
    if configured and configured.lower() not in ("python", "python3"):
        return configured
    return sys.executable


def probe_westlake(python: str) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            [python, "-c", "import westlake"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if completed.returncode == 0:
        return True, ""
    return False, (completed.stderr or completed.stdout or "无法 import westlake").strip()[:800]
