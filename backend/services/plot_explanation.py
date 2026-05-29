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

Write one analytic paragraph (4–6 sentences, English, no bullets). This is a scientific interpretation for a specialist reader, NOT a figure caption.

Required (in this order of emphasis):
1. Chemical mechanisms: which formation/destruction channels, reservoir competition, gas vs surface/mantle coupling, early- vs late-time regimes.
2. Network logic: how plotted species relate (precursor/product, linked hydrogenation, N/C/O redistribution).
3. Physical context from simulation_conditions only when it constrains the chemistry (T, n(H), zeta_CR, phases).
4. Numbers: use at most TWO quantitative callouts (e.g. one dex change or one abundance ratio) as evidence — never enumerate every species with X -> Y.

Forbidden:
- Describing axes, lines, slopes, or "the curve/plot/figure shows".
- Observational disclaimers or "compare with observations" (qualitatively or otherwise).
- Boilerplate such as "gas-phase chemistry and network coupling redistribute abundances over astrophysical time".
- Generic closings reused across figures.
- Inventing species, rates, or detections not in the JSON.

End with ONE mechanism-focused sentence unique to THIS figure (dominant late-time reservoir, timing of a rise, or contrast between two species)."""


_BANNED_EXPLANATION_PHRASES: tuple[str, ...] = (
    "compare with observations only qualitatively",
    "compare with observations",
    "the curve reflects how gas-phase chemistry and network coupling",
    "the curve reflects how gas-phase chemistry",
    "gas-phase chemistry and network coupling in this model",
    "gas-phase chemistry and network coupling",
    "redistribute abundances over astrophysical time",
    "redistribute abundances",
    "interpret these curves as model-predicted",
    "log time versus log abundance",
    "log time vs log abundance",
    "this plot shows",
    "this figure shows",
    "the figure shows",
)

# Clauses containing any of these are dropped entirely (LLM boilerplate).
_BANNED_CLAUSE_MARKERS: tuple[str, ...] = (
    "curve reflects",
    "compare with observations",
    "redistribute abundances",
    "network coupling in this model",
    "only qualitatively",
)


def _sanitize_explanation(text: str) -> str:
    """Remove known boilerplate; drop contaminated sentences/clauses."""
    import re

    cleaned = text.strip()
    if not cleaned:
        return ""

    # Exact recurring closing (often after a semicolon).
    cleaned = re.sub(
        r"The curve reflects how gas-phase chemistry and network coupling in this model\s+"
        r"redistribute abundances over astrophysical time\s*;\s*"
        r"compare with observations only qualitatively\.?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"The curve reflects how gas-phase chemistry and network coupling[^.!?;]*"
        r"redistribute abundances over astrophysical time[^.!?;]*"
        r"compare with observations[^.!?;]*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    for phrase in _BANNED_EXPLANATION_PHRASES:
        idx = cleaned.lower().find(phrase.lower())
        while idx >= 0:
            end = idx + len(phrase)
            while end < len(cleaned) and cleaned[end] in " .;,":
                end += 1
            cleaned = (cleaned[:idx] + cleaned[end:]).strip()
            idx = cleaned.lower().find(phrase.lower())

    kept: list[str] = []
    for part in re.split(r"(?<=[.!?;])\s+", cleaned):
        part = part.strip()
        if part.endswith(";"):
            part = part[:-1].strip()
        if not part:
            continue
        low = part.lower()
        if any(phrase in low for phrase in _BANNED_EXPLANATION_PHRASES):
            continue
        if any(marker in low for marker in _BANNED_CLAUSE_MARKERS):
            continue
        if len(part) < 24 and any(
            frag in low for frag in ("in this model", "the curve", "this plot", "this figure")
        ):
            continue
        kept.append(part)

    cleaned = " ".join(kept)
    cleaned = re.sub(r"\s+", " ", cleaned).replace("..", ".").replace(" ;", ";").strip()
    return cleaned


def sanitize_plot_explanations(plot_data: dict[str, Any]) -> dict[str, Any]:
    """Apply boilerplate removal to all explanation strings in plot_data."""
    explanations = plot_data.get("explanations")
    if not isinstance(explanations, dict):
        return plot_data
    plot_data = dict(plot_data)
    plot_data["explanations"] = {
        str(k): _sanitize_explanation(str(v)) for k, v in explanations.items() if v
    }
    return plot_data


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
    """Brief network context (physical numbers are shown in the UI panel above)."""
    if not conditions:
        return ""
    from backend.services.simulation_conditions import _phase_processes_line

    model = conditions.get("model_label") or conditions.get("model", "this")
    phases = _phase_processes_line(str(conditions.get("model", "")))
    return f"In the {model} setup ({phases}), "


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
    t_peak = entry.get("time_at_peak_yr")
    role = _species_role(name)

    if trend == "increasing":
        timing = ""
        if t_peak is not None:
            timing = f", with most growth before t ~ {float(t_peak):g} yr"
        return (
            f"In sum, {name} is an accumulating reservoir in this run ({_dex_phrase(delta)}{timing}), "
            f"consistent with {role} under the stated physical setup."
        )
    if trend == "decreasing":
        return (
            f"In sum, {name} functions mainly as a precursor or sink ({_dex_phrase(delta)}), "
            f"feeding other network products rather than remaining a late-time gas reservoir."
        )
    return (
        f"In sum, {name} stays near chemical equilibrium after the early phase, "
        f"serving as a stable pool while more reactive tracers evolve."
    )


def _combined_analysis(
    sp_stats: dict[str, dict[str, Any]],
    *,
    t0: float,
    t1: float,
) -> str:
    rising = [n for n, e in sp_stats.items() if e.get("trend") == "increasing"]
    falling = [n for n, e in sp_stats.items() if e.get("trend") == "decreasing"]
    flat = [n for n, e in sp_stats.items() if e.get("trend") == "roughly flat"]
    ranked = _rank_by_final(sp_stats)

    parts = [
        f"Over t ~ {t0:g}–{t1:g} yr the network reallocates reservoirs among the plotted tracers. "
    ]

    if rising and falling:
        parts.append(
            f"Net growth of {', '.join(rising)} alongside depletion of {', '.join(falling)} "
            f"points to coupled gas-phase and surface-return chemistry transferring C/N/O "
            f"from early reservoirs into later products rather than independent scaling. "
        )
    elif len(rising) >= 2:
        parts.append(
            f"Parallel rises in {', '.join(rising)} favour shared hydrogenation or desorption "
            f"sequences feeding multiple organic tracers in this phase model. "
        )
    elif rising:
        parts.append(
            f"{rising[0]} and related products accumulate when formation and/or grain release "
            f"outpace destruction over most of the integration. "
        )

    if flat:
        parts.append(
            f"{', '.join(flat)} stay near chemical balance after the initial transient, "
            f"acting as buffered pools while other species evolve. "
        )

    if ranked:
        dom, y_dom = ranked[0]
        parts.append(
            f"Late-time chemistry is dominated by {_species_role(dom)} "
            f"(order-of-magnitude abundance ~{y_dom:.0e} among the selection). "
        )

    fastest = max(
        ((n, abs(e.get("abundance_change_orders") or 0)) for n, e in sp_stats.items()),
        key=lambda x: x[1],
        default=None,
    )
    if fastest and fastest[1] >= 1 and fastest[0] != (ranked[0][0] if ranked else None):
        n_fast = fastest[0]
        d_fast = sp_stats[n_fast].get("abundance_change_orders")
        parts.append(
            f"The steepest evolution is {n_fast} ({_dex_phrase(d_fast)}), "
            f"marking the most active synthetic or desorption channel in this group. "
        )
    return "".join(parts)


def _single_analysis(name: str, entry: dict[str, Any], *, t0: float, t1: float) -> str:
    trend = entry.get("trend", "changing")
    delta = entry.get("abundance_change_orders")
    t_peak = entry.get("time_at_peak_yr")
    role = _species_role(name)

    if trend == "increasing":
        body = (
            f"{name} behaves as {role}, building up when formation or grain release "
            f"dominates destruction over t ~ {t0:g}–{t1:g} yr ({_dex_phrase(delta)} net change). "
        )
        if t_peak is not None and float(t_peak) < float(t1) * 0.9:
            body += (
                f"Most of the gain occurs before t ~ {float(t_peak):g} yr, after which "
                f"re-processing or slower late-time channels moderate further growth. "
            )
        else:
            body += (
                "Sustained rise implies it is a growing product or released reservoir "
                "in the coupled network, not a passive tracer. "
            )
    elif trend == "decreasing":
        body = (
            f"{name} ({role}) is progressively removed from the gas as it is converted "
            f"into downstream species, photodissociated, or incorporated on grains "
            f"({_dex_phrase(delta)} over the run). "
        )
    elif trend == "roughly flat":
        body = (
            f"{name} ({role}) remains a quasi-steady pool: production and loss stay "
            f"matched after the early adjustment, buffering the network while other "
            f"species evolve over t ~ {t0:g}–{t1:g} yr. "
        )
    else:
        body = (
            f"{name} ({role}) reflects competing channels switching on at different "
            f"epochs ({_dex_phrase(delta)} overall), typical of a species that is "
            f"both formed and destroyed along linked pathways. "
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

    return _sanitize_explanation(f"{ctx}{body}{close}".replace("  ", " ").strip())


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
        "Lead with formation/destruction mechanisms and network coupling — not axes or line shapes.\n"
        "Use at most two numbers from simulation_stats as supporting evidence.\n"
        "Do NOT mention observations or qualitative comparison to data.\n"
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
        cleaned = _sanitize_explanation((content or "").strip())
        return cleaned or None


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
        explanations[label] = _sanitize_explanation(text) if text else text

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
