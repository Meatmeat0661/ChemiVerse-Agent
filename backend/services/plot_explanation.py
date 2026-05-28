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

PLOT_EXPLANATION_SYSTEM = """You explain Westlake/Nautilus gas-phase abundance evolution plots for astrochemistry users.
Rules:
1. Use only the JSON statistics provided; do not invent numerical values or observational claims.
2. State that axes are time (log) vs abundance (log) when relevant.
3. Describe the main trend (rise, fall, plateau) and what it suggests about chemical evolution in the simulation.
4. For combined plots, briefly compare species; for single-species plots, focus on that species only.
5. Write 3–5 sentences in clear English. No bullet lists unless necessary."""


def _normalize_plotted(plot_data: dict[str, Any]) -> list[str]:
    plotted = plot_data.get("plotted") or []
    if isinstance(plotted, str):
        return [s.strip() for s in plotted.split(",") if s.strip()]
    return [str(s).strip() for s in plotted if str(s).strip()]


def _rule_based_explanation(label: str, stats: dict[str, Any], species: list[str]) -> str:
    t0, t1 = stats.get("time_min"), stats.get("time_max")
    if label == "combined":
        intro = (
            f"This combined plot shows log–log abundance evolution from t ≈ {t0:g} to {t1:g} "
            f"for {len(species)} species in the Nautilus network ({', '.join(species)})."
        )
    else:
        intro = (
            f"This plot tracks {label} abundance versus time (log scales) "
            f"from t ≈ {t0:g} to {t1:g} in the Westlake simulation."
        )

    parts = [intro]
    for name in species:
        entry = stats.get("species", {}).get(name)
        if not entry:
            continue
        y0, y1 = entry["initial_abundance"], entry["final_abundance"]
        trend = entry.get("trend", "changing")
        delta = entry.get("abundance_change_orders")
        if delta is not None:
            parts.append(
                f"For {name}, abundance is {trend} by about {abs(delta):.1f} orders of magnitude "
                f"(from {y0:.2e} to {y1:.2e})."
            )
        else:
            parts.append(f"For {name}, abundance is {trend} (from {y0:.2e} to {y1:.2e}).")

    parts.append(
        "The curve reflects how gas-phase chemistry and network coupling in this model "
        "redistribute abundances over astrophysical time; compare with observations only qualitatively."
    )
    return " ".join(parts)


def _minimal_explanation(label: str, species: list[str]) -> str:
    if label == "combined":
        names = ", ".join(species) if species else "selected species"
        return (
            f"This figure shows log–log gas-phase abundance versus time for {names} "
            "from the Westlake/Nautilus simulation. Rising or falling segments indicate "
            "production or destruction in the coupled chemical network over astrophysical time."
        )
    return (
        f"This figure tracks {label} abundance versus time (log scales) in the Westlake simulation. "
        "Changes along the curve reflect how the network sources and sinks this species during evolution."
    )


async def _generate_image_explanation(
    settings: WestlakeSettings,
    *,
    image_label: str,
    stats: dict[str, Any],
    species: list[str],
) -> str | None:
    if not settings.base_url:
        return None

    payload = {
        "image_label": image_label,
        "species_in_plot": species,
        "simulation_stats": stats,
    }
    user_message = (
        f"Explain the evolution plot labeled '{image_label}'.\n\n"
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
                )
                if text:
                    llm_used = True
            except Exception:
                text = None
        if not text:
            if stats:
                text = _rule_based_explanation(label, stats, sp)
            else:
                text = _minimal_explanation(label, sp)
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
