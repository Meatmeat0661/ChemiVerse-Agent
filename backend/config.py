from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class DataSettings(BaseSettings):
    molecules_path: Path = ROOT / "data" / "molecules.json"
    reactions_path: Path = ROOT / "data" / "reactions.json"


class WestlakeSettings(BaseSettings):
    base_url: str = ""
    api_key: str = "not-needed"
    model: str = "westlake"
    timeout_seconds: int = 120


class NautilusSettings(BaseSettings):
    # westlake-tutorial root (contains example_simulation/)
    tutorial_root: Path = Path(
        r"E:/大学/学术项目/Agent-ChemiVerse/westlake-tutorial"
    )
    script: str = "westlake/examples/run_nautilus_network.py"
    plot_script: str = "backend/scripts/plot_westlake.py"  # relative to astrochem-agent root
    default_sim_dir: str = "example_simulation"
    default_species: str = "CO,CH3OH,CH3OCH3"
    default_plot_mode: str = "combined"  # combined | separate | both
    outputs_dir: Path = ROOT / "outputs"
    # 跑 Nautilus 模拟的解释器（建议 3.11/3.12 + westlake + numpy<2）
    python: str = "python"
    # 绘图解释器；留空则与启动 Streamlit 的 Python 相同
    plot_python: str = ""


class ServerSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8765


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASTROCHEM_", env_nested_delimiter="__")

    data: DataSettings = Field(default_factory=DataSettings)
    westlake: WestlakeSettings = Field(default_factory=WestlakeSettings)
    nautilus: NautilusSettings = Field(default_factory=NautilusSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_dict(out[key], value)
        else:
            out[key] = value
    return out


@lru_cache
def get_settings() -> AppSettings:
    # Streamlit Cloud 环境下优先使用相对路径配置，避免本机绝对路径导致加载失败。
    is_cloud = os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud"
    config_path = ROOT / "config.yaml"
    cloud_path = ROOT / "config.cloud.yaml"

    if is_cloud:
        config_path = cloud_path if cloud_path.exists() else config_path
    else:
        if not config_path.exists() and cloud_path.exists():
            config_path = cloud_path

    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    flat: dict[str, Any] = {}
    for section in ("data", "westlake", "nautilus", "server"):
        if section in raw:
            flat[section] = raw[section]

    return AppSettings.model_validate(flat)
