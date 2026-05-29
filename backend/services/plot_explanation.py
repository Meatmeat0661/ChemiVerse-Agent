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

PLOT_LLM_TIMEOUT_SECONDS = 28

PLOT_EXPLANATION_SYSTEM = """You are an astrochemical modeler interpreting Westlake/Nautilus abundance-evolution results.

Write a short analytic paragraph (4–7 sentences, English, no bullets). Prioritize scientific interpretation over figure description.

Required content:
- Network- and phase-appropriate chemistry: formation vs destruction, reservoirs, coupled pathways, early vs late-time behaviour.
- Quantitative support from simulation_stats (abundances, dex changes, trends, time_at_peak_yr when present).
- Physical context from simulation_conditions (density, temperature, zeta_CR, model phases).

Forbidden:
- Generic disclaimers ("this is model output", "not an observation", "interpret these curves").
- Opening with axis labels only ("log time vs log abundance").
- Reusing the same closing sentence you used for another figure.
- Inventing species, rates, or observational comparisons not in the JSON.

End with ONE concluding sentence specific to THIS figure (dominant reservoir, timing of rise/fall, or contrast between species on combined plots)."""


# Conservative network-role hints (educational; not observational claims).
_SPECIES_ROLE: dict[str, str] = {
    "CO": "the main gas-phase CO reservoir that anchors much of the carbon budget",
    "H2": "the H2 pool that sets the hydrogen budget for hydrogenation sequences",
    "CH3OH": "a complex organic tracer often tied to grain-surface hydrogenation and desorption",
    "CH3OCH3": "a larger COM whose gas-phase rise can follow methanol-related surface chemistry",
    "NH3": "a major nitrogen reservoir linked to hydrogenation of N-bearing species",
    "HCN": "a nitrile tracer sensitive to high-T gas-phase and surface-return pathways",
    "H2CO": "a simple organic intermediate between CO hydrogenation and richer COMs",
    "N2": "a stable nitrogen reservoir that constrains how much N is available for NH3/HCN routes",
    "C": "an atomic carbon reservoir coupled to CO and organic interconversion",
    "CH4": "a saturated hydrocarbon tracer of methane-forming channels",
}


def _normalize_plotted(plot_data: dict[str, Any]) -> list[str]:
    plotted = plot_data.get("plotted") or []
    if isinstance(plotted, str):
        return [s.strip() for s in plotted.split(",") if s.strip()]
    return [str(s).strip() for s in plotted if str(s).strip()]


def _conditions_context(conditions: dict[str, Any] | None) -> str:
    if not conditions:
        return ""
    from backend.services.simulation_conditions import _phase_processes_line

    model = conditions.get("model_label") or conditions.get("model", "")
    n_h = conditions.get("n_H_cm3", "")
    temp = conditions.get("T_K", "")
    zeta = conditions.get("zeta_cr_s-1")
    phases = _phase_processes_line(str(conditions.get("model", "")))
    zeta_txt = f", zeta_CR ~ {zeta:g} s^-1" if zeta is not None else ""
    return f"In this {model} network ({phases}; n(H) {n_h}, T {temp}{zeta_txt}), "


def _conditions_for_llm(conditions: dict[str, Any] | None) -> dict[str, Any] | None:
    if not conditions:
        return None
    keys = (
        "model",
        "model_label",
        "n_H_cm3",
        "T_K",
        "zeta_cr_s-1",
        "time_span_yr",
        "initial_abundances_preview",
    )
    slim = {k: conditions[k] for k in keys if conditions.get(k) is not None}
    return slim or None


def _species_role(name: str) -> str:
    return _SPECIES_ROLE.get(name, f"{name} as a coupled tracer in this network")


def _dex_phrase(delta: float | None) -> str:
    if delta is None:
        return "a modest change"
    mag = abs(delta)
    if mag >= 3:
        return f"a strong {mag:.1f}-dex change"
    if mag >= 1:
        return f"a clear {mag:.1f}-dex change"
    return f"a weak {mag:.1f}-dex change"


def _rank_by_final(sp_stats: dict[str, dict[str, Any]]) -> list[tuple[str, float]]:
    ranked = [(n, float(e["final_abundance"])) for n, e in sp_stats.items()]
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def _takeaway_combined(species: list[str], sp_stats: dict[str, dict[str, Any]]) -> str:
    if not sp_stats:
        return "Together, these tracers map how material is redistributed across the network over the integration."

    ranked = _rank_by_final(sp_stats)
    dominant, y_dom = ranked[0]
    runner = ranked[1][0] if len(ranked) > 1 else None

    rising = [
        (n, e["abundance_change_orders"])
        for n, e in sp_stats.items()
        if e.get("trend") == "increasing" and e.get("abundance_change_orders") is not None
    ]
    rising.sort(key=lambda x: abs(x[1] or 0), reverse=True)
    fastest = rising[0][0] if rising else None

    if runner and y_dom > 0 and ranked[1][1] > 0:
        ratio = y_dom / ranked[1][1]
        if ratio >= 10:
            close = (
                f"{dominant} ends as the dominant gas-phase reservoir among the plotted species "
                f"(final abundance ~{y_dom:.1e}), with {runner} trailing by >1 dex."
            )
        else:
            close = (
                f"Late-time chemistry leaves {dominant} and {runner} as comparable reservoirs "
                f"(final abundances within ~1 dex), so neither tracer alone summarizes the run."
            )
    else:
        close = (
            f"By the final time step, {dominant} — {_species_role(dominant)} — "
            f"has the highest abundance among the species shown."
        )

    if fastest and fastest != dominant:
        close += (
            f" The steepest build-up is {fastest}, indicating the most active net production "
            f"or desorption among the plotted set."
        )
    elif fastest == dominant and rising:
        close += f" {dominant} also shows the largest net rise, marking it as the main evolving reservoir in this selection."

    unused = [s for s in species if s not in sp_stats]
    if unused:
        close += f" (Not in pickle: {', '.join(unused)}.)"
    return close


def _takeaway_single(name: str, entry: dict[str, Any]) -> str:
    trend = entry.get("trend", "changing")
    delta = entry.get("abundance_change_orders")
    y0 = float(entry["initial_abundance"])
    y1 = float(entry["final_abundance"])
    t_peak = entry.get("time_at_peak_yr")
    role = _species_role(name)

    if trend == "increasing":
        timing = ""
        if t_peak is not None:
            timing = f", peaking near t ~ {float(t_peak):g} yr before the run ends"
        return (
            f"Overall, {name} acts as {role}: net growth ({_dex_phrase(delta)}; "
            f"{y0:.1e} to {y1:.1e}) marks it as an accumulating product or released reservoir{timing}."
        )
    if trend == "decreasing":
        return (
            f"Overall, {name} ({role}) is net destroyed or locked out of the gas "
            f"({_dex_phrase(delta)}; {y0:.1e} to {y1:.1e}), feeding downstream species rather than staying a late-time reservoir."
        )
    return (
        f"Overall, {name} ({role}) stays near balance ({y0:.1e} to {y1:.1e}), "
        f"so late-time production and loss nearly cancel after the early transient."
    )


def _combined_analysis(
    sp_stats: dict[str, dict[str, Any]],
    *,
    t0: float,
    t1: float,
) -> str:
    parts = [
        f"gas-phase abundances from t ~ {t0:g} to {t1:g} yr are compared. "
    ]
    for name, entry in sp_stats.items():
        y0, y1 = entry["initial_abundance"], entry["final_abundance"]
        trend = entry.get("trend", "changing")
        delta = entry.get("abundance_change_orders")
        parts.append(
            f"{name} ({_species_role(name)}) is {trend} ({_dex_phrase(delta)}; "
            f"{y0:.1e} -> {y1:.1e}); "
        )

    rising = [n for n, e in sp_stats.items() if e.get("trend") == "increasing"]
    falling = [n for n, e in sp_stats.items() if e.get("trend") == "decreasing"]
    flat = [n for n, e in sp_stats.items() if e.get("trend") == "roughly flat"]

    if rising and falling:
        parts.append(
            f"The anti-correlated evolution of {', '.join(rising)} versus {', '.join(falling)} "
            f"is consistent with transfer of C/N/O-bearing material through linked gas-phase and "
            f"surface-return routes rather than a single uniform scaling. "
        )
    elif len(rising) >= 2:
        parts.append(
            f"Co-rising {', '.join(rising)} suggests shared hydrogenation or desorption pathways "
            f"feeding multiple COM tracers in this phase model. "
        )
    if flat:
        parts.append(
            f"{', '.join(flat)} remain near steady state, implying matched formation and destruction "
            f"after the initial adjustment. "
        )
    return "".join(parts)


def _single_analysis(name: str, entry: dict[str, Any], *, t0: float, t1: float) -> str:
    y0, y1 = entry["initial_abundance"], entry["final_abundance"]
    trend = entry.get("trend", "changing")
    delta = entry.get("abundance_change_orders")
    t_peak = entry.get("time_at_peak_yr")
    role = _species_role(name)

    body = (
        f"{name} ({role}) evolves from {y0:.1e} to {y1:.1e} between t ~ {t0:g} and {t1:g} yr "
        f"with a {trend} trend ({_dex_phrase(delta)}). "
    )
    if trend == "increasing" and t_peak is not None and float(t_peak) < float(t1) * 0.9:
        body += (
            f"The abundance peaks near t ~ {float(t_peak):g} yr, so much of the net gain occurs "
            f"before the final epoch—late times may reflect re-processing or approach to a slower regime. "
        )
    elif trend == "decreasing":
        body += (
            "The decline implies efficient consumption as a precursor, photodissociation target, "
            "or freeze-out sink in the coupled gas–grain network. "
        )
    elif trend == "roughly flat":
        body += (
            "The weak net trend suggests the species sits near a quasi-steady reservoir after "
            "the early-time adjustment. "
        )
    else:
        body += (
            "The non-monotonic shape points to competing formation and destruction channels "
            "active at different evolutionary stages. "
        )
    return body


def _rule_based_explanation(
    label: str,
    stats: dict[str, Any],
    species: list[str],
    *,
    conditions: dict[str, Any] | None = None,
) -> str:
    sp_stats = {
        n: stats["species"][n]
        for n in species
        if n in stats.get("species", {})
    }
    t0, t1 = stats.get("time_min"), stats.get("time_max")
    ctx = _conditions_context(conditions)

    if label == "combined":
        body = _combined_analysis(sp_stats, t0=float(t0), t1=float(t1))
        close = _takeaway_combined(species, sp_stats)
    else:
        entry = sp_stats.get(label)
        if not entry:
            return _minimal_explanation(label, species, conditions=conditions)
        body = _single_analysis(label, entry, t0=float(t0), t1=float(t1))
        close = _takeaway_single(label, entry)

    return f"{ctx}{body}{close}".replace("  ", " ").strip()


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
            + f"Relative evolution of {names} traces how the network reallocates C/N/O reservoirs "
            f"across gas-phase and surface-linked channels; compare which species rise or fall together "
            f"to infer coupled synthetic routes."
        )
    return (
        ctx
        + f"The {label} trace reflects the balance of formation, destruction, and (in multi-phase models) "
        f"surface exchange for {_species_role(label)}; slope changes mark shifts between net source "
        f"and sink behaviour over the integration."
    )


async def _generate_image_explanation(
    settings: WestlakeSettings,
    *,
    image_label: str,
    stats: dict[str, Any],
    species: list[str],
    conditions: dict[str, Any] | None = None,
    other_explanations: dict[str, str] | None = None,
) -> str | None:
    if not settings.base_url:
        return None

    plot_kind = "combined_multi_species" if image_label == "combined" else "single_species"
    payload = {
        "image_label": image_label,
        "plot_kind": plot_kind,
        "species_in_plot": species,
        "simulation_stats": stats,
        "simulation_conditions": _conditions_for_llm(conditions),
    }
    user_message = (
        f"Write the astrochemical interpretation for figure '{image_label}' only "
        f"({plot_kind}; species: {', '.join(species) or 'see stats'}).\n"
        "Lead with science, not axis description. Use numbers from simulation_stats.\n"
        "The final sentence must be unique to this figure.\n\n"
        f"Context JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    if other_explanations:
        snippets = []
        for other_label, text in other_explanations.items():
            if other_label == image_label:
                continue
            snippet = " ".join(text.split())[:280]
            snippets.append(f"- [{other_label}]: {snippet}…")
        if snippets:
            user_message += (
                "\n\nAlready written for other figures — do NOT reuse their wording or closing lines:\n"
                + "\n".join(snippets)
            )

    url = settings.base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    body = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": PLOT_EXPLANATION_SYSTEM},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.45,
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
                    other_explanations=explanations,
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
