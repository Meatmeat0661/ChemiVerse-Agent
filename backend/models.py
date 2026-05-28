from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="SMILES, key (e.g. CCH), or formula (e.g. C2H)")
    include_reactions: bool = True
    use_llm: bool = True


class SimulationRequest(BaseModel):
    sim_dir: str | None = None
    use_evolution: bool = True
    plot: bool = True
    plot_mode: str = Field(
        default="combined",
        description="combined: one figure; separate: one PNG per species; both",
    )
    include_images_base64: bool = Field(
        default=False,
        description="Embed PNG as base64 in response (for remote Streamlit clients)",
    )
    species: list[str] = Field(
        default_factory=list,
        description="Species to plot; empty uses config default_species",
    )
    extra_args: list[str] = Field(default_factory=list)


class PlotRequest(BaseModel):
    sim_dir: str | None = None
    species: list[str] = Field(default_factory=list)
    plot_mode: str = "combined"
    include_images_base64: bool = False
    include_explanations: bool = Field(
        default=True,
        description="Generate per-plot AI captions from res.pickle statistics (requires westlake LLM or uses fallback text)",
    )
    run_id: str | None = None


class Observation(BaseModel):
    id: int
    source: str
    origin: list[str] | None = None


class MoleculeRecord(BaseModel):
    key: str
    atoms: dict[str, int]
    smiles: str | None = None
    inchi: str | None = None
    name: str | None = None
    normal_formula: str | None = None
    num_atoms: int | None = None
    ma: float | None = None
    charge: int | None = None
    num_rings: int | None = None
    empirical_formulae: list[str] = Field(default_factory=list)
    desorption_energy: list[Any] = Field(default_factory=list)
    observations: list[Observation] | None = None


class ReactionSpecies(BaseModel):
    name: str
    num: int
    is_special: bool = False


class ReactionParam(BaseModel):
    id: int
    alpha: float | None = None
    beta: float | None = None
    gamma: float | None = None
    formula: str | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    origin: list[str] = Field(default_factory=list)
    comment: str | None = None


class ReactionRecord(BaseModel):
    key: str
    reactants: list[ReactionSpecies]
    products: list[ReactionSpecies]
    reaction_type: str | None = None
    params: list[ReactionParam] = Field(default_factory=list)


class AgentResponse(BaseModel):
    query: str
    resolved_key: str | None
    molecule: MoleculeRecord | None
    reactions_as_reactant: list[ReactionRecord]
    reactions_as_product: list[ReactionRecord]
    summary: str
    llm_used: bool
