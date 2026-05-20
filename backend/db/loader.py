from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.models import MoleculeRecord, ReactionRecord


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("molecules", "reactions", "data", "items"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
        return list(payload.values())
    raise ValueError(f"Unsupported JSON root in {path}")


class AstroChemDatabase:
    def __init__(self, molecules_path: Path, reactions_path: Path) -> None:
        self.molecules_path = molecules_path
        self.reactions_path = reactions_path
        self._molecules: list[MoleculeRecord] | None = None
        self._reactions: list[ReactionRecord] | None = None
        self._molecule_by_key: dict[str, MoleculeRecord] | None = None
        self._alias_to_key: dict[str, str] | None = None

    def reload(self) -> None:
        self._molecules = None
        self._reactions = None
        self._molecule_by_key = None
        self._alias_to_key = None

    @property
    def molecules(self) -> list[MoleculeRecord]:
        if self._molecules is None:
            raw = _load_json_list(self.molecules_path)
            self._molecules = [MoleculeRecord.model_validate(item) for item in raw]
        return self._molecules

    @property
    def reactions(self) -> list[ReactionRecord]:
        if self._reactions is None:
            raw = _load_json_list(self.reactions_path)
            self._reactions = [ReactionRecord.model_validate(item) for item in raw]
        return self._reactions

    @property
    def molecule_by_key(self) -> dict[str, MoleculeRecord]:
        if self._molecule_by_key is None:
            self._molecule_by_key = {m.key: m for m in self.molecules}
        return self._molecule_by_key

    @property
    def alias_to_key(self) -> dict[str, str]:
        if self._alias_to_key is None:
            mapping: dict[str, str] = {}
            for molecule in self.molecules:
                aliases = {molecule.key}
                if molecule.normal_formula:
                    aliases.add(molecule.normal_formula)
                if molecule.smiles:
                    aliases.add(molecule.smiles)
                aliases.update(molecule.empirical_formulae)
                if molecule.name:
                    aliases.add(molecule.name)
                for alias in aliases:
                    mapping[_normalize(alias)] = molecule.key
            self._alias_to_key = mapping
        return self._alias_to_key


def _normalize(value: str) -> str:
    return value.strip()
