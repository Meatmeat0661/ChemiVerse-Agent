from __future__ import annotations

from backend.models import ReactionParam, ReactionRecord


def _format_origin(param: ReactionParam) -> str:
    if param.origin:
        label = ", ".join(param.origin[:2])
        if len(param.origin) > 2:
            label += " …"
        return label
    return f"id={param.id}"


def _format_temp_range(param: ReactionParam) -> str:
    if param.temp_min is None and param.temp_max is None:
        return "—"
    return f"{param.temp_min} .. {param.temp_max}"


def format_rate_param(param: ReactionParam) -> str:
    parts = []
    if param.alpha is not None:
        parts.append(f"α={param.alpha}")
    if param.beta is not None:
        parts.append(f"β={param.beta}")
    if param.gamma is not None:
        parts.append(f"γ={param.gamma}")
    temp = _format_temp_range(param)
    if temp != "—":
        parts.append(f"T∈{temp} K")
    text = " ".join(parts) if parts else "—"
    return f"[{_format_origin(param)}] {text}"


def reaction_equation(rxn: ReactionRecord) -> str:
    left = " + ".join(f"{s.num}×{s.name}{'†' if s.is_special else ''}" for s in rxn.reactants)
    right = " + ".join(f"{s.num}×{s.name}{'†' if s.is_special else ''}" for s in rxn.products)
    return f"{left} → {right}"


def reaction_table_rows(rxn: ReactionRecord) -> list[dict[str, object]]:
    """One table row per rate source (params entry)."""
    equation = reaction_equation(rxn)
    rtype = rxn.reaction_type or "未知类型"

    if not rxn.params:
        return [
            {
                "key": rxn.key,
                "反应": equation,
                "类型": rtype,
                "来源": "—",
                "α": "—",
                "β": "—",
                "γ": "—",
                "T范围(K)": "—",
            }
        ]

    rows: list[dict[str, object]] = []
    for idx, param in enumerate(rxn.params):
        rows.append(
            {
                "key": rxn.key if idx == 0 else "",
                "反应": equation if idx == 0 else "",
                "类型": rtype if idx == 0 else "",
                "来源": _format_origin(param),
                "α": param.alpha if param.alpha is not None else "—",
                "β": param.beta if param.beta is not None else "—",
                "γ": param.gamma if param.gamma is not None else "—",
                "T范围(K)": _format_temp_range(param),
            }
        )
    return rows


def param_records_for_dataframe(rxn: ReactionRecord) -> list[dict[str, object]]:
    """Rows for detailed param sub-tables (reaction query expander)."""
    if not rxn.params:
        return []
    return [
        {
            "来源": _format_origin(p),
            "α": p.alpha,
            "β": p.beta,
            "γ": p.gamma,
            "T范围(K)": _format_temp_range(p),
            "formula": p.formula or "",
            "comment": p.comment or "",
        }
        for p in rxn.params
    ]
