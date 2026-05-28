from __future__ import annotations

import math
from pathlib import Path
from typing import Any


def _log10_safe(value: float) -> float | None:
    if value <= 0:
        return None
    return math.log10(value)


def extract_plot_stats(
    sim_dir: Path,
    species: list[str],
    *,
    t_start: float = 1.0,
) -> dict[str, Any]:
    """Summarize abundance evolution from res.pickle for LLM / rule-based captions."""
    try:
        import westlake
    except ImportError as exc:
        raise RuntimeError("westlake is required to read res.pickle") from exc

    res_path = sim_dir / "res.pickle"
    if not res_path.exists():
        raise FileNotFoundError(f"Missing {res_path}")

    res = westlake.load_result(res_path)
    mask = res.time > t_start
    times = res.time[mask]
    if len(times) == 0:
        raise ValueError(f"No time points above t_start={t_start}")

    available = set(res.species)
    requested = [name.strip() for name in species if name.strip()]
    plotted = [name for name in requested if name in available]

    species_stats: dict[str, Any] = {}
    for name in plotted:
        series = res[name][mask]
        y0 = float(series[0])
        y1 = float(series[-1])
        ymin = float(series.min())
        ymax = float(series.max())
        log0 = _log10_safe(y0)
        log1 = _log10_safe(y1)
        delta_orders = None
        if log0 is not None and log1 is not None:
            delta_orders = round(log1 - log0, 2)

        if y1 > y0 * 1.5:
            trend = "increasing"
        elif y1 < y0 * 0.67:
            trend = "decreasing"
        else:
            trend = "roughly flat"

        species_stats[name] = {
            "initial_abundance": y0,
            "final_abundance": y1,
            "min_abundance": ymin,
            "max_abundance": ymax,
            "abundance_change_orders": delta_orders,
            "trend": trend,
        }

    return {
        "simulation_directory": sim_dir.name,
        "time_min": float(times[0]),
        "time_max": float(times[-1]),
        "t_start_cutoff": t_start,
        "plotted_species": plotted,
        "missing_species": [name for name in requested if name not in available],
        "species": species_stats,
    }


def species_for_image_label(label: str, stats: dict[str, Any]) -> list[str]:
    if label == "combined":
        return list(stats.get("species", {}).keys())
    if label in stats.get("species", {}):
        return [label]
    return stats.get("plotted_species", [])
