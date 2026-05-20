from __future__ import annotations

import json
from typing import Any

import httpx

from backend.config import WestlakeSettings
from backend.models import MoleculeRecord, ReactionRecord


SYSTEM_PROMPT = """你是天体化学助手。根据提供的分子数据库与反应网络记录回答用户问题。
规则：
1. 只使用上下文中的数据库字段；不要编造观测来源、速率常数或分子量。
2. 若数据缺失，明确说明“数据库未提供”。
3. 反应速率参数使用 KIDA 形式 k = alpha * T^beta * exp(-gamma/T)，并注明温度范围。
4. 用中文回答，结构清晰：分子标识、物性、观测、相关反应、注意事项。"""


def _compact_molecule(molecule: MoleculeRecord) -> dict[str, Any]:
    return molecule.model_dump(exclude_none=True)


def _compact_reactions(reactions: list[ReactionRecord], limit: int = 40) -> list[dict[str, Any]]:
    return [reaction.model_dump(exclude_none=True) for reaction in reactions[:limit]]


def build_context(
    query: str,
    molecule: MoleculeRecord | None,
    as_reactant: list[ReactionRecord],
    as_product: list[ReactionRecord],
) -> str:
    payload = {
        "user_query": query,
        "molecule": _compact_molecule(molecule) if molecule else None,
        "reactions_as_reactant": _compact_reactions(as_reactant),
        "reactions_as_product": _compact_reactions(as_product),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


async def generate_summary(
    settings: WestlakeSettings,
    query: str,
    molecule: MoleculeRecord | None,
    as_reactant: list[ReactionRecord],
    as_product: list[ReactionRecord],
) -> str | None:
    if not settings.base_url:
        return None

    context = build_context(query, molecule, as_reactant, as_product)
    user_message = f"用户查询：{query}\n\n数据库上下文：\n{context}"

    url = settings.base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.api_key}"}
    body = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
