"""Nautilus / Westlake 运行环境检测."""

from __future__ import annotations

import subprocess
import sys


def resolve_python(configured: str, *, prefer_streamlit: bool = False) -> str:
    """解析用于子进程的 Python 路径。

    - 配置了具体路径 → 使用该路径（模拟推荐 3.11/3.12 + westlake）
    - `python` / `python3` / 空 → 默认 `sys.executable`（与 Streamlit 一致，适合绘图）
    """
    configured = (configured or "").strip()
    if configured and configured.lower() not in ("python", "python3"):
        return configured
    return sys.executable


def probe_numpy_for_westlake(python: str) -> tuple[bool, str]:
    """westlake 模拟依赖 numpy 1.x（numpy 2 会报 in1d 等错误）。"""
    script = (
        "import numpy as np; "
        "v = tuple(int(x) for x in np.__version__.split('.')[:2]); "
        "assert v[0] < 2, f'numpy {np.__version__} 过高，请 pip install \"numpy<2\"'; "
        "print(np.__version__)"
    )
    try:
        completed = subprocess.run(
            [python, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if completed.returncode == 0:
        return True, (completed.stdout or "").strip()
    return False, (completed.stderr or completed.stdout or "numpy 检查失败").strip()[:800]


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


def probe_plot_deps(python: str) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            [python, "-c", "import matplotlib; import westlake"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if completed.returncode == 0:
        return True, ""
    return False, (completed.stderr or completed.stdout or "绘图依赖缺失").strip()[:800]
