from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx

from backend.config import WestlakeSettings
from backend.services.plot_stats import (
    extract_plot_stats,
    extract_plot_stats_subprocess,
    species_for_image_label,
)

PLOT_LLM_TIMEOUT_SECONDS = 20

PLOT_EXPLANATION_SYSTEM = """You write astrochemical interpretations of Westlake/Nautilus gas-phase abundance evolution plots.

Your job is NOT merely to describe the figure. Provide:
1. A brief description of axes and main trends (log time vs log abundance).
2. Scientific analysis: what the evolution implies about formation, destruction, and coupling in the chemical network under the stated physical conditions.
3. Meaning for the user: why the relative behaviour of species matters (e.g. early vs late chemistry, major reservoirs, linked pathways) in this simulation scenario.
4. For combined plots, compare species quantitatively using the JSON stats; for single-species plots, focus on that species.

Rules:
- Use only numbers and conditions from the JSON; do not invent abundances, rates, or observational detections.
- Mention n(H), T, Av, zeta_CR, and model type when provided in simulation_conditions.
- Do not claim agreement with a specific source or object unless given in the data.
- Write 4–7 sentences in clear English as a short analytic paragraph (no bullet lists)."""


def _normalize_plotted(plot_data: dict[str, Any]) -> list[str]:
    plotted = plot_data.get("plotted") or []
    if isinstance(plotted, str):
        return [s.strip() for s in plotted.split(",") if s.strip()]
    return [str(s).strip() for s in plotted if str(s).strip()]


def _conditions_context(conditions: dict[str, Any] | None) -> str:
    if not conditions:
        return ""
    model = conditions.get("model_label") or conditions.get("model", "")
    medium = conditions.get("medium_mode", "")
    n_h = conditions.get("n_H_cm3", "")
    temp = conditions.get("T_K", "")
    av = conditions.get("Av_mag", "")
    zeta = conditions.get("zeta_cr_s-1")
    zeta_txt = f", cosmic-ray ionization rate zeta_CR ≈ {zeta:g} s^-1" if zeta is not None else ""
    return (
        f"Under the {model} setup ({medium}), with n(H) {n_h}, T {temp}, A_V {av}{zeta_txt}, "
        f"gas-phase abundances evolve as follows. "
    )


def _trend_interpretation(name: str, trend: str, delta: float | None) -> str:
    if trend == "increasing" and delta is not None and delta >= 2:
        return (
            f"{name} is a net product over most of the run (rise ≈ {abs(delta):.1f} dex), "
            "suggesting efficient gas-phase and/or surface-linked formation pathways in this network."
        )
    if trend == "decreasing":
        return (
            f"{name} is depleted over time, indicating it acts mainly as a reactant, photodissociation "
            "target, or sink in the coupled network at these conditions."
        )
    if trend == "roughly flat":
        return (
            f"{name} stays near chemical equilibrium (weak net trend), so production and loss "
            "are roughly balanced after the early transient."
        )
    return f"{name} shows a non-trivial evolution, reflecting competition between formation and destruction channels."


def _rule_based_explanation(
    label: str,
    stats: dict[str, Any],
    species: list[str],
    *,
    conditions: dict[str, Any] | None = None,
) -> str:
    t0, t1 = stats.get("time_min"), stats.get("time_max")
    parts: list[str] = [_conditions_context(conditions)]

    if label == "combined":
        parts.append(
            f"This combined log–log plot tracks gas-phase abundances from t ≈ {t0:g} to {t1:g} yr "
            f"for {', '.join(species)}. "
        )
    else:
        parts.append(
            f"This plot follows {label} (log abundance vs log time) from t ≈ {t0:g} to {t1:g} yr. "
        )

    trends: list[tuple[str, str, float | None]] = []
    for name in species:
        entry = stats.get("species", {}).get(name)
        if not entry:
            continue
        y0, y1 = entry["initial_abundance"], entry["final_abundance"]
        trend = entry.get("trend", "changing")
        delta = entry.get("abundance_change_orders")
        trends.append((name, trend, delta))
        if delta is not None:
            parts.append(
                f"{name} {trend} by about {abs(delta):.1f} orders of magnitude "
                f"({y0:.2e} → {y1:.2e}); "
            )
        else:
            parts.append(f"{name} is {trend} ({y0:.2e} → {y1:.2e}); ")

    if len(trends) >= 2:
        rising = [n for n, tr, d in trends if tr == "increasing"]
        falling = [n for n, tr, _ in trends if tr == "decreasing"]
        if rising and falling:
            parts.append(
                f"Comparing species, {', '.join(rising)} build up while {', '.join(falling)} decline, "
                "which points to redistribution of C-, O-, and N-bearing material through the network "
                "rather than uniform scaling of all tracers. "
            )
        elif len(rising) >= 2:
            parts.append(
                f"Several species ({', '.join(rising)}) rise together, consistent with linked "
                "synthetic routes (e.g. progressive hydrogenation or surface return) in this model. "
            )

    for name, trend, delta in trends:
        parts.append(_trend_interpretation(name, trend, delta) + " ")

    parts.append(
        "Interpret these curves as model-predicted chemical evolution for the stated physical scenario; "
        "they illustrate which species become major reservoirs and when, not a direct match to a specific observation."
    )
    return "".join(parts).replace("  ", " ").strip()


def _minimal_explanation(
    label: str,
    species: list[str],
    *,
    conditions: dict[str, Any] | None = None,
) -> str:
    ctx = _conditions_context(conditions)
    if label == "combined":
        names = ", ".join(species) if species else "selected species"
        return (
            ctx
            + f"This figure shows log–log gas-phase abundance versus time for {names}. "
            "Rising segments indicate net formation or release into the gas; falling segments indicate "
            "chemical consumption or freeze-out in the coupled network. "
            "Together, the curves show which species dominate at early vs late evolutionary stages in this model."
        )
    return (
        ctx
        + f"This figure tracks {label} abundance versus time (log scales). "
        "The slope reflects the balance of formation and destruction; a sustained rise marks a growing reservoir, "
        "while a decline marks a species mainly converted into other network products under these conditions."
    )


async def _generate_image_explanation(
    settings: WestlakeSettings,
    *,
    image_label: str,
    stats: dict[str, Any],
    species: list[str],
    conditions: dict[str, Any] | None = None,
) -> str | None:
    if not settings.base_url:
        return None

    payload = {
        "image_label": image_label,
        "species_in_plot": species,
        "simulation_stats": stats,
        "simulation_conditions": conditions,
    }
    user_message = (
        f"Interpret the astrochemical meaning of the evolution plot labeled '{image_label}'. "
        "Do not only describe the lines: explain what the trends imply for chemistry in this "
        "simulation (formation vs destruction, relative species roles, timing), using the JSON below.\n\n"
        f"Context JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    url = settings.base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    body = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": PLOT_EXPLANATION_SYSTEM},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.35,
    }

    timeout = httpx.Timeout(5.0, read=float(PLOT_LLM_TIMEOUT_SECONDS))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return (content or "").strip() or None


async def build_plot_explanations_async(
    sim_dir: Path,
    plot_data: dict[str, Any],
    westlake_settings: WestlakeSettings,
    *,
    python_exe: str | None = None,
) -> dict[str, Any]:
    """Return plot_data with explanations dict keyed by image label."""
    images = plot_data.get("images") or []
    if not images or plot_data.get("returncode", 1) != 0:
        return plot_data

    species = _normalize_plotted(plot_data)
    stats: dict[str, Any] | None = None
    stats_errors: list[str] = []

    try:
        stats = extract_plot_stats(sim_dir, species)
    except Exception as exc:
        stats_errors.append(str(exc))
        if python_exe:
            try:
                stats = extract_plot_stats_subprocess(sim_dir, species, python_exe)
            except Exception as sub_exc:
                stats_errors.append(str(sub_exc))

    if stats is None:
        plot_data["explanation_error"] = "; ".join(stats_errors) if stats_errors else "Could not read res.pickle"

    conditions: dict[str, Any] | None = None
    try:
        from backend.services.simulation_conditions import load_simulation_conditions

        conditions = load_simulation_conditions(sim_dir)
    except Exception:
        conditions = None

    explanations: dict[str, str] = {}
    llm_used = False
    all_species = species or _normalize_plotted(plot_data)

    for img in images:
        label = str(img.get("label") or img.get("filename") or "plot")
        if label.endswith(".png"):
            label = Path(label).stem
        sp = species_for_image_label(label, stats) if stats else (
            all_species if label == "combined" else [label]
        )
        text: str | None = None
        if stats and westlake_settings.base_url:
            try:
                text = await _generate_image_explanation(
                    westlake_settings,
                    image_label=label,
                    stats=stats,
                    species=sp,
                    conditions=conditions,
                )
                if text:
                    llm_used = True
            except Exception:
                text = None
        if not text:
            if stats:
                text = _rule_based_explanation(label, stats, sp, conditions=conditions)
            else:
                text = _minimal_explanation(label, sp, conditions=conditions)
        explanations[label] = text

    plot_data["explanations"] = explanations
    plot_data["explanation_llm_used"] = llm_used
    return plot_data


def attach_plot_explanations(
    sim_dir: Path,
    plot_data: dict[str, Any],
    westlake_settings: WestlakeSettings,
    *,
    python_exe: str | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        build_plot_explanations_async(
            sim_dir, plot_data, westlake_settings, python_exe=python_exe
        )
    )
