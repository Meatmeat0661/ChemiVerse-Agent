from __future__ import annotations

from backend.db.loader import AstroChemDatabase
from backend.db.resolver import find_reactions_for_species, get_molecule, species_names_for_molecule
from backend.models import AgentResponse, MoleculeRecord, ReactionParam, ReactionRecord
from backend.services.westlake_llm import generate_summary


def _format_rate_param(param: ReactionParam) -> str:
    parts = []
    if param.alpha is not None:
        parts.append(f"α={param.alpha}")
    if param.beta is not None:
        parts.append(f"β={param.beta}")
    if param.gamma is not None:
        parts.append(f"γ={param.gamma}")
    if param.temp_min is not None or param.temp_max is not None:
        parts.append(f"T∈[{param.temp_min}, {param.temp_max}] K")
    if param.origin:
        parts.append(f"来源: {', '.join(param.origin)}")
    return "; ".join(parts)


def _summarize_reaction(reaction: ReactionRecord) -> str:
    left = " + ".join(
        f"{s.num}×{s.name}{'†' if s.is_special else ''}" for s in reaction.reactants
    )
    right = " + ".join(
        f"{s.num}×{s.name}{'†' if s.is_special else ''}" for s in reaction.products
    )
    rate_lines = [_format_rate_param(p) for p in reaction.params]
    rate_text = " | ".join(rate_lines) if rate_lines else "无速率参数"
    rtype = reaction.reaction_type or "未知类型"
    return f"{reaction.key}: {left} → {right} [{rtype}] ({rate_text})"


def rule_based_summary(
    query: str,
    key: str | None,
    molecule: MoleculeRecord | None,
    as_reactant: list[ReactionRecord],
    as_product: list[ReactionRecord],
    *,
    list_reactions: bool = True,
) -> str:
    if not molecule:
        return (
            f'No species matching "{query}" was found in the molecule database '
            "(supports key, SMILES, normal_formula, empirical_formulae)."
        )

    obs_list = molecule.observations or []
    obs_sources = sorted({o.source for o in obs_list})
    lines = [
        f"## 分子：{molecule.key}",
        f"- 标准式：{molecule.normal_formula or '—'}",
        f"- SMILES：{molecule.smiles or '—'}",
        f"- InChI：{molecule.inchi or '—'}",
        f"- 分子量 ma：{molecule.ma if molecule.ma is not None else '—'}",
        f"- 电荷：{molecule.charge if molecule.charge is not None else '—'}",
        f"- 环数：{molecule.num_rings if molecule.num_rings is not None else '—'}",
        f"- 原子组成：{molecule.atoms}",
    ]
    if obs_sources:
        preview = ", ".join(obs_sources[:12])
        suffix = f" 等共 {len(obs_sources)} 处" if len(obs_sources) > 12 else ""
        lines.append(f"- 观测源（节选）：{preview}{suffix}")
    else:
        lines.append("- 观测源：数据库未提供")

    lines.append("")
    if list_reactions:
        lines.append(f"## 作为反应物（{len(as_reactant)} 条）")
        if as_reactant:
            for reaction in as_reactant:
                lines.append(f"- {_summarize_reaction(reaction)}")
        else:
            lines.append("- 无匹配反应")

        lines.append("")
        lines.append(f"## 作为产物（{len(as_product)} 条）")
        if as_product:
            for reaction in as_product:
                lines.append(f"- {_summarize_reaction(reaction)}")
        else:
            lines.append("- 无匹配反应")
    else:
        lines.append(
            f"## 相关反应\n"
            f"- 作为反应物：{len(as_reactant)} 条\n"
            f"- 作为产物：{len(as_product)} 条\n"
            f"- 详细速率见结果表格。"
        )

    if key and key != query.strip():
        lines.append("")
        lines.append(f"_解析：用户输入「{query}」→ 库内 key「{key}」_")
    return "\n".join(lines)


class AstroChemAgent:
    def __init__(self, db: AstroChemDatabase) -> None:
        self.db = db

    async def answer(
        self,
        query: str,
        include_reactions: bool = True,
        use_llm: bool = True,
        westlake_settings=None,
    ) -> AgentResponse:
        key, molecule = get_molecule(self.db, query)
        as_reactant: list[ReactionRecord] = []
        as_product: list[ReactionRecord] = []

        if molecule and include_reactions:
            names = species_names_for_molecule(molecule)
            as_reactant, as_product = find_reactions_for_species(self.db, names)

        summary = rule_based_summary(
            query,
            key,
            molecule,
            as_reactant,
            as_product,
            list_reactions=not include_reactions,
        )
        llm_used = False

        if use_llm and westlake_settings and westlake_settings.base_url:
            try:
                llm_text = await generate_summary(
                    westlake_settings,
                    query,
                    molecule,
                    as_reactant,
                    as_product,
                )
                if llm_text:
                    summary = llm_text
                    llm_used = True
            except Exception as exc:  # noqa: BLE001
                summary += f"\n\n> Westlake LLM 调用失败，已回退规则摘要：{exc}"

        return AgentResponse(
            query=query,
            resolved_key=key,
            molecule=molecule,
            reactions_as_reactant=as_reactant,
            reactions_as_product=as_product,
            summary=summary,
            llm_used=llm_used,
        )
