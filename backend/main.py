from __future__ import annotations

import os
import subprocess
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import ROOT, get_settings
from backend.db.loader import AstroChemDatabase
from backend.models import PlotExplainRequest, PlotRequest, QueryRequest, SimulationRequest
from backend.services.agent import AstroChemAgent
from backend.services.nautilus import NautilusRunner

settings = get_settings()
db = AstroChemDatabase(settings.data.molecules_path, settings.data.reactions_path)
agent = AstroChemAgent(db)
nautilus = NautilusRunner(settings.nautilus)
FRONTEND = ROOT / "frontend"
SIMULATION_API_KEY = os.getenv("SIMULATION_API_KEY", "")


def verify_simulation_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if SIMULATION_API_KEY and x_api_key != SIMULATION_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        db.molecules  # preload
        db.reactions
    except FileNotFoundError:
        pass
    yield


app = FastAPI(title="Astrochem Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    molecules_ok = settings.data.molecules_path.exists()
    reactions_ok = settings.data.reactions_path.exists()
    nautilus_ok = nautilus.script_path().exists()
    return {
        "status": "ok",
        "molecules_path": str(settings.data.molecules_path),
        "reactions_path": str(settings.data.reactions_path),
        "molecules_loaded": molecules_ok,
        "reactions_loaded": reactions_ok,
        "tutorial_root": str(nautilus.tutorial_root()),
        "nautilus_script": str(nautilus.script_path()),
        "nautilus_ready": nautilus_ok,
        "simulation_api_key_required": bool(SIMULATION_API_KEY),
        "plot_script": str(nautilus.plotter.plot_script_path()),
        "westlake_llm_configured": bool(settings.westlake.base_url),
    }


@app.post("/api/query")
async def query_molecule(body: QueryRequest):
    try:
        return await agent.answer(
            body.query,
            include_reactions=body.include_reactions,
            use_llm=body.use_llm,
            westlake_settings=settings.westlake,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/molecules/search")
def search_molecules(q: str = "", limit: int = 20):
    q = q.strip().lower()
    results = []
    for molecule in db.molecules:
        haystack = " ".join(
            filter(
                None,
                [
                    molecule.key,
                    molecule.normal_formula,
                    molecule.smiles,
                    molecule.name,
                    *molecule.empirical_formulae,
                ],
            )
        ).lower()
        if not q or q in haystack:
            results.append(
                {
                    "key": molecule.key,
                    "smiles": molecule.smiles,
                    "normal_formula": molecule.normal_formula,
                }
            )
        if len(results) >= limit:
            break
    return {"items": results}


@app.post("/api/simulation/run", dependencies=[Depends(verify_simulation_api_key)])
def run_simulation(body: SimulationRequest):
    try:
        species = body.species or None
        if body.plot:
            return nautilus.run_with_plot(
                sim_dir=body.sim_dir,
                use_evolution=body.use_evolution,
                species=species,
                plot_mode=body.plot_mode,
                include_images_base64=body.include_images_base64,
                extra_args=body.extra_args,
                timeout=3600,
            )
        return nautilus.run(
            sim_dir=body.sim_dir,
            use_evolution=body.use_evolution,
            extra_args=body.extra_args,
            timeout=3600,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Simulation timed out") from exc


@app.post("/api/simulation/plot", dependencies=[Depends(verify_simulation_api_key)])
def plot_simulation(body: PlotRequest):
    from backend.services.plot_lock import release_plot_lock, try_acquire_plot_lock

    if not try_acquire_plot_lock(timeout=600.0):
        raise HTTPException(
            status_code=503,
            detail="Plot queue busy (another plot is running). Wait ~1 min and try again.",
        )
    try:
        sim_dir = nautilus.simulation_dir(body.sim_dir)
        pickle_path = sim_dir / "res.pickle"
        if not pickle_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"No res.pickle in {sim_dir}. Run simulation first.",
            )
        species = body.species or None
        result = nautilus.plotter.plot(
            sim_dir=sim_dir,
            species=species,
            run_id=body.run_id,
            mode=body.plot_mode,  # type: ignore[arg-type]
            include_images_base64=body.include_images_base64,
        )
        if body.include_explanations and result.get("returncode") == 0:
            from backend.services.plot_explanation import attach_plot_explanations

            try:
                result = attach_plot_explanations(
                    sim_dir,
                    result,
                    settings.westlake,
                    python_exe=nautilus.python_executable(),
                )
            except Exception as exc:  # noqa: BLE001
                result["explanation_error"] = str(exc)
                result.setdefault("explanations", {})
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Plotting timed out") from exc
    finally:
        release_plot_lock()


@app.post("/api/simulation/plot/explain", dependencies=[Depends(verify_simulation_api_key)])
def explain_plot(body: PlotExplainRequest):
    """Generate plot captions only (fast follow-up after /api/simulation/plot)."""
    sim_dir = nautilus.simulation_dir(body.sim_dir)
    pickle_path = sim_dir / "res.pickle"
    if not pickle_path.exists():
        raise HTTPException(status_code=404, detail=f"No res.pickle in {sim_dir}")

    images = body.images or [{"label": "combined"}]
    plot_data: dict[str, object] = {
        "returncode": 0,
        "plotted": body.species,
        "images": images,
    }
    from backend.services.plot_explanation import attach_plot_explanations

    try:
        return attach_plot_explanations(
            sim_dir,
            plot_data,
            settings.westlake,
            python_exe=nautilus.python_executable(),
        )
    except Exception as exc:  # noqa: BLE001
        plot_data["explanation_error"] = str(exc)
        plot_data["explanations"] = {}
        plot_data["explanation_llm_used"] = False
        return plot_data


OUTPUTS = settings.nautilus.outputs_dir
if not OUTPUTS.is_absolute():
    OUTPUTS = ROOT / OUTPUTS
OUTPUTS.mkdir(parents=True, exist_ok=True)


@app.get("/api/simulation/conditions", dependencies=[Depends(verify_simulation_api_key)])
def simulation_conditions(sim_dir: str | None = None):
    """Return physical setup metadata for a Westlake/Nautilus simulation directory."""
    from backend.services.simulation_conditions import load_simulation_conditions

    path = nautilus.simulation_dir(sim_dir)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Simulation directory not found: {path}")
    return load_simulation_conditions(path)


@app.get("/api/outputs/{run_id}/{filename}")
def get_output_image(run_id: str, filename: str):
    if ".." in run_id or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    path = OUTPUTS / run_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/simulation/preview")
def preview_simulation(sim_dir: str | None = None, use_evolution: bool = True):
    return {
        "command": nautilus.build_command(sim_dir=sim_dir, use_evolution=use_evolution),
        "cwd": str(nautilus.tutorial_root()),
        "sim_dir": str(nautilus.simulation_dir(sim_dir)),
    }


@app.post("/api/admin/reload")
def reload_database():
    db.reload()
    return {"status": "reloaded"}


if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND / "index.html")
