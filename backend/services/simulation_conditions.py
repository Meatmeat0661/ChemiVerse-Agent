from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import yaml


_MODEL_LABELS = {
    "simple": "Gas-phase only",
    "two phase": "Two-phase (gas + grain surface)",
    "three phase": "Three-phase (gas + surface + mantle)",
}


def _fmt_sci(value: float, *, sig: int = 2) -> str:
    if value == 0:
        return "0"
    return f"{value:.{sig}g}"


def _read_structure_evolution(path: Path) -> list[dict[str, float]] | None:
    if not path.exists():
        return None
    rows: list[dict[str, float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("!"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        t_yr, log_av, log_n, log_t = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
        rows.append(
            {
                "time_yr": t_yr,
                "Av": 10**log_av,
                "n_H_cm3": 10**log_n,
                "T_K": 10**log_t,
            }
        )
    return rows or None


def _summarize_evolution(rows: list[dict[str, float]]) -> dict[str, str]:
    av0, av1 = rows[0]["Av"], rows[-1]["Av"]
    n0, n1 = rows[0]["n_H_cm3"], rows[-1]["n_H_cm3"]
    t0, t1 = rows[0]["T_K"], rows[-1]["T_K"]
    ty0, ty1 = rows[0]["time_yr"], rows[-1]["time_yr"]

    def span(a: float, b: float, *, unit: str = "") -> str:
        if abs(a - b) / max(abs(a), abs(b), 1e-99) < 0.01:
            return f"{_fmt_sci(a)}{unit}"
        return f"{_fmt_sci(a)} → {_fmt_sci(b)}{unit}"

    return {
        "time_span_yr": span(ty0, ty1, unit=" yr"),
        "Av": span(av0, av1, unit=" mag"),
        "n_H": span(n0, n1, unit=" cm⁻³"),
        "temperature": span(t0, t1, unit=" K"),
    }


def _read_initial_abundances(path: Path, *, max_lines: int = 12) -> list[str]:
    if not path.exists():
        return []
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("!"):
            continue
        if "=" not in line:
            continue
        name, _, rest = line.partition("=")
        name = name.strip()
        value = rest.split("!")[0].strip()
        lines.append(f"{name} = {value}")
        if len(lines) >= max_lines:
            lines.append("…")
            break
    return lines


def load_simulation_conditions(sim_dir: Path) -> dict[str, Any]:
    """Read Westlake/Nautilus physical setup from a simulation directory."""
    sim_dir = sim_dir.resolve()
    config_path = sim_dir / "config.yml"
    config: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config = loaded if isinstance(loaded, dict) else {}

    model_key = str(config.get("model", "unknown"))
    model_label = _MODEL_LABELS.get(model_key, model_key)

    structure_path = sim_dir / "structure_evolution.dat"
    evolution_rows = _read_structure_evolution(structure_path)
    use_evolution = evolution_rows is not None

    conditions: dict[str, Any] = {
        "sim_dir": sim_dir.name,
        "sim_path": str(sim_dir),
        "model": model_key,
        "model_label": model_label,
        "use_structure_evolution": use_evolution,
        "has_res_pickle": (sim_dir / "res.pickle").exists(),
        "zeta_cr_s-1": config.get("zeta_cr"),
        "zeta_xr_s-1": config.get("zeta_xr"),
        "uv_flux": config.get("uv_flux"),
        "dtg_mass_ratio": config.get("dtg_mass_ratio"),
        "t_end_yr": config.get("t_end"),
        "plot_abundance_definition": "Gas-phase species (names in gas_species.in)",
        "processes_note": (
            "Gas-phase reactions (gas_reactions.in) + grain-surface chemistry "
            "(grain_reactions.in, surface_parameters.in)."
        ),
    }

    if use_evolution and evolution_rows:
        ev = _summarize_evolution(evolution_rows)
        conditions["medium_mode"] = "Time-dependent (structure_evolution.dat)"
        conditions["time_span_yr"] = ev["time_span_yr"]
        conditions["Av_mag"] = ev["Av"]
        conditions["n_H_cm3"] = ev["n_H"]
        conditions["T_K"] = ev["temperature"]
        conditions["integration_t_end_yr"] = evolution_rows[-1]["time_yr"]
    else:
        conditions["medium_mode"] = "Uniform (config.yml)"
        conditions["Av_mag"] = config.get("Av")
        conditions["n_H_cm3"] = config.get("den_gas")
        conditions["T_K"] = f"gas {config.get('T_gas')} K, dust {config.get('T_dust')} K"
        conditions["integration_t_end_yr"] = config.get("t_end")

    conditions["initial_abundances_preview"] = _read_initial_abundances(sim_dir / "abundances.in")
    return conditions


def _phase_processes_line(model: str) -> str:
    """Whether gas / surface / mantle chemistry is included in the network."""
    key = (model or "").strip().lower()
    gas, surface, mantle = True, False, False
    if key == "simple":
        pass
    elif key == "three phase":
        surface, mantle = True, True
    else:
        surface = True
    return (
        f"Gas phase: {'yes' if gas else 'no'} · "
        f"Surface: {'yes' if surface else 'no'} · "
        f"Mantle: {'yes' if mantle else 'no'}"
    )


def conditions_to_rows(info: dict[str, Any]) -> list[tuple[str, str]]:
    """Label/value pairs for Physical conditions (six fields)."""
    rows: list[tuple[str, str]] = [
        ("Density n(H)", str(info.get("n_H_cm3", "—"))),
        ("Temperature", str(info.get("T_K", "—"))),
    ]
    zeta = info.get("zeta_cr_s-1")
    if zeta is not None:
        rows.append(("Cosmic-ray ionization rate zeta_CR", f"{_fmt_sci(float(zeta))} s^-1"))
    else:
        rows.append(("Cosmic-ray ionization rate zeta_CR", "—"))

    preview = info.get("initial_abundances_preview") or []
    if preview:
        ab = "; ".join(p for p in preview if p != "…")
        if any(p == "…" for p in preview):
            ab = f"{ab}; …" if ab else "…"
        rows.append(("Initial abundances (relative to H)", ab))
    else:
        rows.append(("Initial abundances (relative to H)", "—"))

    time_span = info.get("time_span_yr")
    if time_span:
        rows.append(("Time range", str(time_span)))
    elif info.get("integration_t_end_yr") is not None:
        rows.append(("Time range", f"0 → {_fmt_sci(float(info['integration_t_end_yr']))} yr"))
    else:
        rows.append(("Time range", "—"))

    rows.append(("Phases / processes", _phase_processes_line(str(info.get("model", "")))))
    return rows


def conditions_to_html(info: dict[str, Any]) -> str:
    """Bulleted HTML list with distinct label vs value styling for Streamlit."""
    items = []
    for label, value in conditions_to_rows(info):
        items.append(
            "<li>"
            f'<span class="pc-label">{html.escape(label)}</span>'
            f'<span class="pc-value">{html.escape(value)}</span>'
            "</li>"
        )
    return f'<ul class="physical-conditions-list">{"".join(items)}</ul>'


def conditions_to_markdown(info: dict[str, Any]) -> str:
    """Plain markdown fallback (prefer conditions_to_html in Streamlit)."""
    return "\n\n".join(f"**{label}:** {value}" for label, value in conditions_to_rows(info))
