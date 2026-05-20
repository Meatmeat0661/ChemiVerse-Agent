from __future__ import annotations

from backend.db.loader import AstroChemDatabase
from backend.models import MoleculeRecord, ReactionRecord


def resolve_molecule_key(db: AstroChemDatabase, query: str) -> str | None:
    normalized = query.strip()
    if not normalized:
        return None

    if normalized in db.molecule_by_key:
        return normalized

    alias_key = db.alias_to_key.get(normalized)
    if alias_key:
        return alias_key

    # Case-insensitive fallback for keys and formulas
    lower = normalized.lower()
    for molecule in db.molecules:
        candidates = [molecule.key, molecule.normal_formula, molecule.smiles, *molecule.empirical_formulae]
        if molecule.name:
            candidates.append(molecule.name)
        for candidate in candidates:
            if candidate and candidate.lower() == lower:
                return molecule.key
    return None


def species_names_for_molecule(molecule: MoleculeRecord) -> set[str]:
    names = {molecule.key}
    if molecule.normal_formula:
        names.add(molecule.normal_formula)
    names.update(molecule.empirical_formulae)
    if molecule.name:
        names.add(molecule.name)
    return names


def find_reactions_for_species(
    db: AstroChemDatabase,
    species_names: set[str],
) -> tuple[list[ReactionRecord], list[ReactionRecord]]:
    normalized = {name.strip() for name in species_names if name}
    as_reactant: list[ReactionRecord] = []
    as_product: list[ReactionRecord] = []

    for reaction in db.reactions:
        reactant_names = {s.name for s in reaction.reactants}
        product_names = {s.name for s in reaction.products}
        if reactant_names & normalized:
            as_reactant.append(reaction)
        if product_names & normalized:
            as_product.append(reaction)
    return as_reactant, as_product


def get_molecule(db: AstroChemDatabase, query: str) -> tuple[str | None, MoleculeRecord | None]:
    key = resolve_molecule_key(db, query)
    if not key:
        return None, None
    return key, db.molecule_by_key.get(key)
