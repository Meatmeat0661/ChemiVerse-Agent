"""ChemiVerse Astrochem Agent — Streamlit UI."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import streamlit as st

from backend.config import get_settings
from backend.db.loader import AstroChemDatabase
from backend.services.agent import AstroChemAgent
from backend.services.reaction_display import reaction_table_rows

import sys

_UI_ROOT = Path(__file__).resolve().parent / "streamlit_ui"
if str(_UI_ROOT) not in sys.path:
    sys.path.insert(0, str(_UI_ROOT))

from theme import apply_starry_theme

st.set_page_config(
    page_title="BIRDS-ARDCA",
    page_icon="🌌",
    layout="wide",
)



def render_app_branding() -> None:
    st.markdown(
        """
<div class="birds-header">
  <div class="birds-header-inner">
    <h1 class="birds-title">BIRDS-ARDCA</h1>
    <p class="birds-subtitle">(Astrochemical Reaction Database and Chemical-evolution Agent under BIRDS-AI)</p>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def is_streamlit_cloud() -> bool:
    return os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud"


def _apply_secrets_to_settings(settings):
    try:
        data = st.secrets.get("data", {})
        if data.get("molecules_path"):
            settings.data.molecules_path = Path(data["molecules_path"])
        if data.get("reactions_path"):
            settings.data.reactions_path = Path(data["reactions_path"])
        westlake = st.secrets.get("westlake", {})
        if westlake.get("base_url"):
            settings.westlake.base_url = str(westlake["base_url"]).strip()
        if westlake.get("api_key"):
            settings.westlake.api_key = str(westlake["api_key"])
        if westlake.get("model"):
            settings.westlake.model = str(westlake["model"])
    except Exception:
        pass
    return settings


@st.cache_resource
def load_resources():
    settings = _apply_secrets_to_settings(get_settings())
    mol_path = settings.data.molecules_path
    rxn_path = settings.data.reactions_path
    root = Path(__file__).resolve().parent
    if not mol_path.is_absolute():
        mol_path = root / mol_path
    if not rxn_path.is_absolute():
        rxn_path = root / rxn_path
    db = AstroChemDatabase(mol_path, rxn_path)
    agent = AstroChemAgent(db)
    on_cloud = is_streamlit_cloud()
    nautilus = None
    if not on_cloud:
        from backend.services.nautilus import NautilusRunner

        nautilus = NautilusRunner(settings.nautilus)
    return settings, db, agent, nautilus, on_cloud


def run_async(coro):
    return asyncio.run(coro)


def sidebar_status(settings, db, nautilus) -> None:
    st.sidebar.header("System Status")
    mol_ok = settings.data.molecules_path.exists()
    rxn_ok = settings.data.reactions_path.exists()
    st.sidebar.write("Molecule DB", "✅" if mol_ok else "❌")
    st.sidebar.write("Reaction DB", "✅" if rxn_ok else "❌")
    if nautilus is not None:
        st.sidebar.write("Westlake Script", "✅" if nautilus.script_path().exists() else "❌")
    else:
        st.sidebar.write("Westlake", "— (Cloud query mode)")
    if mol_ok and rxn_ok:
        try:
            st.sidebar.caption(f"Loaded {len(db.molecules)} molecules · {len(db.reactions)} reactions")
        except Exception as exc:
            st.sidebar.warning(f"Load failed: {exc}")
    with st.sidebar.expander("Path Configuration"):
        lines = [
            f"molecules:\n{settings.data.molecules_path}",
            f"reactions:\n{settings.data.reactions_path}",
        ]
        if nautilus is not None:
            lines.append(f"tutorial:\n{nautilus.tutorial_root()}")
        st.code("\n\n".join(lines), language=None)
    if st.sidebar.button("Reload Database"):
        load_resources.clear()
        st.rerun()


def page_query(agent: AstroChemAgent, db: AstroChemDatabase, settings) -> None:
    st.header("Molecule Query")
    st.caption("Supports SMILES, species key (e.g., CCH), and molecular formula (e.g., C2H, N2).")

    examples = ["N2", "CCH", "[C]#C", "CO", "HCN", "NH3", "CH3OH", "H2O"]
    ex_cols = st.columns(len(examples))
    for col, ex in zip(ex_cols, examples):
        if col.button(ex, use_container_width=True):
            st.session_state["query_input"] = ex

    query = st.text_input(
        "Query",
        placeholder="e.g., N2, [C]#C, CH3OH",
        key="query_input",
    )

    include_reactions = st.checkbox("Include related reactions", value=True)

    if st.button("Search", type="primary", disabled=not query.strip()):
        with st.spinner("Searching..."):
            result = run_async(
                agent.answer(
                    query.strip(),
                    include_reactions=include_reactions,
                    use_llm=False,
                    westlake_settings=settings.westlake,
                )
            )

        if not result.molecule:
            st.error(result.summary)
            return

        st.success(f"Resolved to **{result.resolved_key}**")

        m = result.molecule
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Molecular Mass (ma)", f"{m.ma}" if m.ma else "—")
        c2.metric("Charge", m.charge if m.charge is not None else "—")
        c3.metric("Ring Count", m.num_rings if m.num_rings is not None else "—")
        c4.metric("Atom Count", m.num_atoms if m.num_atoms else "—")

        obs = m.observations or []
        if obs:
            st.subheader(f"Observations ({len(obs)})")
            st.dataframe(
                [{"source": o.source, "refs": len(o.origin or [])} for o in obs[:200]],
                use_container_width=True,
            )
            if len(obs) > 200:
                st.caption("Showing first 200 observations only")

        if include_reactions:
            st.subheader("Related Reactions")
            t1, t2 = st.tabs(
                [f"As Reactant ({len(result.reactions_as_reactant)})", f"As Product ({len(result.reactions_as_product)})"]
            )

            def reaction_table(reactions):
                rows = []
                for rxn in reactions:
                    rows.extend(reaction_table_rows(rxn))
                st.caption(f"{len(reactions)} reactions · {len(rows)} rows (multiple rate sources shown separately)")
                st.dataframe(rows, use_container_width=True)

            with t1:
                reaction_table(result.reactions_as_reactant)
            with t2:
                reaction_table(result.reactions_as_product)

        st.session_state["plot_species"] = result.resolved_key or query.strip()


def simulation_api_config() -> tuple[str | None, str]:
    try:
        block = st.secrets.get("simulation_api", {})
        base = (block.get("base_url") or "").strip().rstrip("/")
        key = (block.get("api_key") or "").strip()
        if base:
            return base, key
    except Exception:
        pass
    base = os.getenv("SIMULATION_API_URL", "").strip().rstrip("/")
    key = os.getenv("SIMULATION_API_KEY", "").strip()
    return (base, key) if base else (None, key)


def simulation_admin_mode_enabled(on_cloud: bool) -> bool:
    if not on_cloud:
        return True
    try:
        block = st.secrets.get("admin", {})
        admin_key = (block.get("simulation_key") or "").strip()
    except Exception:
        admin_key = ""
    if not admin_key:
        return False

    st.sidebar.markdown("### Admin Mode")
    token = st.sidebar.text_input("Simulation admin key", type="password", key="legacy_sim_admin_key")
    enabled = token.strip() == admin_key
    if enabled:
        st.sidebar.success("Real-time simulation enabled (admin)")
    return enabled


EVOLUTION_PLOT_CTX = "evolution_plot_ctx"


def _plot_images_ready(plot_data: dict) -> bool:
    images = plot_data.get("images") or []
    if not images:
        return bool(plot_data.get("image_path"))
    return any(img.get("base64") for img in images)


def _format_simulation_api_error(exc: Exception, api_base: str | None = None) -> str:
    msg = str(exc)
    lower = msg.lower()
    if "503" in msg or "plot queue busy" in lower:
        return (
            f"Server is busy ({msg}). Another plot is still running — wait ~1 minute "
            "and click Plot once."
        )
    if "111" in msg or "connection refused" in lower:
        host = api_base or "simulation API"
        return (
            f"Simulation API is not running ({msg}). Nothing is listening at {host}. "
            "Start uvicorn on the server and open port 8765 in the firewall."
        )
    if "104" in msg or "connection reset" in lower or "econnreset" in lower:
        host = api_base or "simulation API"
        return (
            f"Simulation server closed the connection ({msg}). "
            f"The service at {host} may be stopped, restarting, or out of memory. "
            "Restart the API on the server and check memory/disk."
        )
    if "connect" in lower or "timed out" in lower or "timeout" in lower:
        return (
            f"Cannot reach simulation server{f' at {api_base}' if api_base else ''}: {msg}. "
            "Ensure the instance is running and port 8765 is open."
        )
    return msg


def _plot_api_succeeded(plot_data: dict) -> bool:
    if plot_data.get("returncode", 1) != 0:
        return False
    if plot_data.get("images"):
        return True
    return bool(plot_data.get("image_path"))


def _evolution_plot_ready() -> bool:
    ctx = st.session_state.get(EVOLUTION_PLOT_CTX)
    if not ctx:
        return False
    return _plot_api_succeeded(ctx.get("plot_data") or {})


def _plot_action_buttons(plot_key: str, explain_key: str) -> tuple[bool, bool]:
    ready = _evolution_plot_ready()
    col_plot, col_explain = st.columns(2, gap="medium")
    with col_plot:
        plot_clicked = st.button("Plot", type="primary", key=plot_key, use_container_width=True)
    with col_explain:
        if ready:
            explain_clicked = st.button(
                "AI Explanation",
                type="primary",
                key=explain_key,
                use_container_width=True,
            )
        else:
            explain_clicked = st.button(
                "AI Explanation",
                type="secondary",
                disabled=True,
                key=explain_key,
                use_container_width=True,
            )
    if not ready:
        st.caption(
            'After plotting, you can click "AI Explanation" button to generate '
            "explanation for this plot."
        )
    return plot_clicked, explain_clicked


PHYSICAL_CONDITIONS_CACHE = "physical_conditions_cache"


def _load_simulation_conditions(
    *,
    sim_dir_path: Path | None = None,
    sim_dir_name: str | None = None,
    api_base: str | None = None,
    api_key: str = "",
) -> dict | None:
    try:
        if api_base:
            from backend.services.simulation_api import RemoteSimulationClient

            client = RemoteSimulationClient(api_base, api_key=api_key)
            return client.get_conditions(sim_dir_name or "example_simulation")
        if sim_dir_path is not None:
            from backend.services.simulation_conditions import load_simulation_conditions

            return load_simulation_conditions(sim_dir_path)
    except Exception as exc:
        return {"error": str(exc)}
    return None


def _render_physical_conditions_panel(
    *,
    sim_dir_path: Path | None = None,
    sim_dir_name: str | None = None,
    api_base: str | None = None,
    api_key: str = "",
) -> None:
    """Fixed block below Plot — simulation setup does not depend on plotted species."""
    sim_key = sim_dir_name or "example_simulation"
    cache_key = f"{api_base or 'local'}:{sim_key}"
    cache = st.session_state.setdefault(PHYSICAL_CONDITIONS_CACHE, {})
    if cache_key not in cache:
        cache[cache_key] = _load_simulation_conditions(
            sim_dir_path=sim_dir_path,
            sim_dir_name=sim_key,
            api_base=api_base,
            api_key=api_key,
        )
    info = cache[cache_key]

    st.markdown("#### Physical conditions")
    if not info:
        st.caption("Physical conditions unavailable.")
        return
    if info.get("error"):
        st.caption(f"Physical conditions unavailable: {info['error']}")
        return
    from backend.services.simulation_conditions import conditions_to_html

    st.markdown(
        f'<div class="physical-conditions-card">{conditions_to_html(info)}</div>',
        unsafe_allow_html=True,
    )


def _slim_plot_data_for_session(plot_data: dict) -> dict:
    import copy

    slim = copy.deepcopy(plot_data)
    for img in slim.get("images") or []:
        if img.get("url"):
            img.pop("base64", None)
    return slim


def _ensure_plot_images_displayable(
    plot_data: dict,
    api_base: str | None,
    *,
    api_key: str = "",
) -> dict:
    if _plot_images_ready(plot_data):
        return plot_data
    if api_base:
        return _hydrate_remote_plot_images(plot_data, api_base, api_key=api_key)
    return plot_data


def _hydrate_remote_plot_images(
    plot_data: dict,
    api_base: str,
    *,
    api_key: str = "",
) -> dict:
    """Server-side fetch when base64 missing (browser cannot load http:// on HTTPS pages)."""
    import base64

    import httpx

    images = plot_data.get("images") or []
    if not images or not api_base:
        return plot_data

    headers = {"X-API-Key": api_key} if api_key else {}
    base = api_base.rstrip("/")
    errors: list[str] = []
    with httpx.Client(timeout=120) as client:
        for img in images:
            if img.get("base64"):
                continue
            rel = img.get("url") or ""
            if not rel:
                continue
            url = f"{base}{rel}" if rel.startswith("/") else rel
            try:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                img["base64"] = base64.b64encode(response.content).decode("ascii")
            except Exception as exc:
                errors.append(f"{url}: {exc}")
    if errors and not _plot_images_ready(plot_data):
        plot_data["image_load_error"] = "; ".join(errors[:3])
    return plot_data


def _store_evolution_plot_ctx(
    plot_data: dict,
    *,
    sim_dir_name: str | None,
    species_list: list[str],
    sim_dir_path: Path | None = None,
    api_base: str | None = None,
    api_key: str = "",
) -> None:
    st.session_state[EVOLUTION_PLOT_CTX] = {
        "plot_data": _slim_plot_data_for_session(plot_data),
        "sim_dir_name": sim_dir_name,
        "species_list": species_list,
        "sim_dir_path": str(sim_dir_path) if sim_dir_path else None,
        "api_base": api_base,
        "api_key": api_key,
    }


def _render_stored_evolution_plot(settings, default_api_base: str | None = None, default_api_key: str = "") -> None:
    ctx = st.session_state.get(EVOLUTION_PLOT_CTX)
    if not ctx:
        return
    plot_data = ctx.get("plot_data")
    if not plot_data:
        return
    import copy

    plot_data = copy.deepcopy(plot_data)
    sim_dir_path = Path(ctx["sim_dir_path"]) if ctx.get("sim_dir_path") else None
    show_plot_results(
        plot_data,
        settings,
        api_base=ctx.get("api_base") or default_api_base,
        sim_dir_path=sim_dir_path,
        sim_dir_name=ctx.get("sim_dir_name"),
        api_key=ctx.get("api_key") or default_api_key,
        species_list=ctx.get("species_list"),
    )


def _simulation_form(settings, default_species_key: str = "plot_species"):
    if default_species_key not in st.session_state:
        st.session_state[default_species_key] = ""
    sim_dir = settings.nautilus.default_sim_dir
    species_text = st.text_input(
        "Species to plot (comma-separated)",
        key=default_species_key,
        placeholder="e.g. N2,NH3,HCN,H2CO",
    )
    # Fixed to one combined figure for simpler UX
    plot_mode = "combined"
    use_evolution = True
    plot_after = True
    st.info("Examples: `N2,NH3,HCN,H2CO` or `CO,CH3OH,CH3OCH3`", icon="💡")
    species_list = [s.strip() for s in species_text.replace("，", ",").split(",") if s.strip()]
    return sim_dir, species_list, plot_mode, use_evolution, plot_after


def page_simulation_local(nautilus, settings, allow_run_sim: bool = True) -> None:
    st.header("Westlake Evolution + Plotting (Local)")
    st.caption("Runs directly on local westlake installation.")

    sim_dir, species_list, plot_mode, use_evolution, plot_after = _simulation_form(settings)
    plot_clicked, explain_clicked = _plot_action_buttons("local_plot", "local_explain")
    sim_path = nautilus.simulation_dir(sim_dir or None)
    _render_physical_conditions_panel(sim_dir_path=sim_path, sim_dir_name=sim_dir)

    if plot_clicked:
        if not species_list:
            st.warning("Enter at least one species to plot (comma-separated).")
            return
        with st.spinner("Plotting..."):
            try:
                sim_path = nautilus.simulation_dir(sim_dir or None)
                if not (sim_path / "res.pickle").exists():
                    st.error(f"{sim_path / 'res.pickle'} not found. Please generate simulation results first.")
                    st.session_state.pop(EVOLUTION_PLOT_CTX, None)
                    return
                plot_data = nautilus.plotter.plot(
                    sim_dir=sim_path,
                    species=species_list or None,
                    mode=plot_mode,
                    include_images_base64=True,
                )
            except Exception as exc:
                st.error(str(exc))
                st.session_state.pop(EVOLUTION_PLOT_CTX, None)
                return

        if plot_data.get("returncode", 1) != 0:
            st.session_state.pop(EVOLUTION_PLOT_CTX, None)
            show_plot_results(plot_data, settings, sim_dir_path=sim_path, sim_dir_name=sim_dir)
            return

        _store_evolution_plot_ctx(
            plot_data,
            sim_dir_name=sim_dir,
            species_list=species_list,
            sim_dir_path=sim_path,
        )
        st.rerun()

    if explain_clicked and _evolution_plot_ready():
        ctx = st.session_state[EVOLUTION_PLOT_CTX]
        sim_path = Path(ctx["sim_dir_path"]) if ctx.get("sim_dir_path") else None
        with st.spinner("Generating AI explanation..."):
            explained = _fetch_plot_explanations(
                dict(ctx["plot_data"]),
                settings,
                sim_dir_path=sim_path,
                sim_dir_name=ctx.get("sim_dir_name"),
                species_list=ctx.get("species_list"),
                force_refresh=True,
            )
            ctx["plot_data"] = explained
        st.session_state[EVOLUTION_PLOT_CTX] = ctx
        st.rerun()

    _render_stored_evolution_plot(settings)


def page_simulation_remote(api_base: str, api_key: str, settings, allow_run_sim: bool = True) -> None:
    from backend.services.simulation_api import RemoteSimulationClient

    st.header("Westlake Evolution + Plotting")

    client = RemoteSimulationClient(api_base, api_key=api_key)
    sim_dir, species_list, plot_mode, use_evolution, plot_after = _simulation_form(settings)
    plot_clicked, explain_clicked = _plot_action_buttons("remote_plot", "remote_explain")
    _render_physical_conditions_panel(
        sim_dir_name=sim_dir,
        api_base=api_base,
        api_key=api_key,
    )

    if plot_clicked:
        if not species_list:
            st.warning("Enter at least one species to plot (comma-separated).")
            return
        if st.session_state.get("plot_in_progress"):
            st.warning("A plot request is already running. Please wait — do not click Plot again.")
            return
        st.session_state["plot_in_progress"] = True
        plot_data = None
        try:
            with st.spinner("Plotting..."):
                plot_data = client.plot_only(
                    sim_dir=sim_dir or None,
                    plot_mode=plot_mode,
                    species=species_list or None,
                    include_explanations=False,
                    include_images_base64=False,
                )
            plot_data = _ensure_plot_images_displayable(
                plot_data, api_base, api_key=api_key
            )
        except Exception as exc:
            st.error(_format_simulation_api_error(exc, api_base))
            st.session_state.pop(EVOLUTION_PLOT_CTX, None)
            return
        finally:
            st.session_state["plot_in_progress"] = False

        if not plot_data or plot_data.get("returncode", 1) != 0:
            st.session_state.pop(EVOLUTION_PLOT_CTX, None)
            show_plot_results(
                plot_data,
                settings,
                api_base=api_base,
                api_key=api_key,
                sim_dir_name=sim_dir,
                species_list=species_list,
            )
            return

        _store_evolution_plot_ctx(
            plot_data,
            sim_dir_name=sim_dir,
            species_list=species_list,
            api_base=api_base,
            api_key=api_key,
        )
        st.rerun()

    if explain_clicked and _evolution_plot_ready():
        ctx = st.session_state[EVOLUTION_PLOT_CTX]
        with st.spinner("Generating AI explanation..."):
            explained = _fetch_plot_explanations(
                dict(ctx["plot_data"]),
                settings,
                sim_dir_name=ctx.get("sim_dir_name"),
                api_base=ctx.get("api_base") or api_base,
                api_key=ctx.get("api_key") or api_key,
                species_list=ctx.get("species_list"),
                force_refresh=True,
            )
            ctx["plot_data"] = _slim_plot_data_for_session(explained)
        st.session_state[EVOLUTION_PLOT_CTX] = ctx
        st.rerun()

    _render_stored_evolution_plot(settings, default_api_base=api_base, default_api_key=api_key)


def load_simulation_catalog() -> list[dict]:
    root = Path(__file__).resolve().parent
    path = root / "data" / "simulation_catalog.json"
    if not path.exists():
        return []
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def page_simulation_static() -> None:
    st.header("Westlake Evolution Plots (Precomputed)")
    st.caption(
        "Precomputed locally with [astro-westlake](https://gitee.com/yqiuu/astro-westlake) and published to GitHub; "
        "visitors do not need westlake or dedicated servers."
    )
    catalog = load_simulation_catalog()
    if not catalog:
        st.warning("No precomputed plots available. Maintainers can run `python scripts/publish_plots_to_repo.py --help` locally.")
        st.code(
            "python scripts/publish_plots_to_repo.py --id nitrogen-default "
            "--species N2,NH3,HCN,H2CO --run",
            language="bash",
        )
        return

    root = Path(__file__).resolve().parent
    labels = [f"{e.get('title', e['id'])} ({', '.join(e.get('species', []))})" for e in catalog]
    choice = st.selectbox("Select scenario", range(len(catalog)), format_func=lambda i: labels[i])
    entry = catalog[choice]
    st.markdown(f"**{entry.get('title', entry['id'])}**")
    st.caption(entry.get("description", ""))

    images = entry.get("images") or []
    if not images:
        st.warning("No images available for this scenario.")
        return

    st.success(f"{len(images)} image(s)")
    cols = st.columns(min(3, len(images)) or 1)
    for idx, img in enumerate(images):
        path = root / img["file"]
        with cols[idx % len(cols)]:
            st.caption(img.get("label", path.name))
            if path.exists():
                st.image(str(path), use_container_width=True)
            else:
                st.warning(f"Missing: {img['file']}")


def page_simulation_unavailable(on_cloud: bool) -> None:
    catalog = load_simulation_catalog()
    if catalog:
        page_simulation_static()
        return

    st.header("Westlake Evolution")
    st.warning("Real-time evolution plotting is currently unavailable.")
    st.markdown(
        """
**Recommended without dedicated servers (precomputed gallery):**

1. Install westlake once on your local machine  
2. Generate PNGs with the script and push to GitHub  
3. Streamlit Cloud serves static images; visitors install nothing

```powershell
pip install -e E:\\...\\westlake-tutorial\\westlake
python scripts/publish_plots_to_repo.py --id nitrogen-default --species N2,NH3,HCN,H2CO --run
git add data/plots data/simulation_catalog.json
git push
```

**Why not run westlake directly on Streamlit Cloud?**  
The free tier has tight memory/runtime limits; installing torch+westlake and running evolution jobs often fails or times out.

If you need visitor-defined real-time plotting, use a dedicated simulation API server (see `DEPLOY_SIMULATION_SERVER.md`).
        """
    )


def _plot_image_label(img: dict) -> str:
    label = str(img.get("label") or img.get("filename") or "plot")
    if label.endswith(".png"):
        label = Path(label).stem
    return label


def _render_plot_explanation(text: str) -> None:
    import html

    from backend.services.plot_explanation import _sanitize_explanation

    text = _sanitize_explanation(text)
    if not text:
        return
    body = html.escape(text).replace("\n", "<br/>")
    st.markdown(
        f'<div class="plot-explanation-card"><strong>About this plot</strong><br/><br/>{body}</div>',
        unsafe_allow_html=True,
    )


def _fetch_plot_explanations(
    plot_data: dict,
    settings,
    *,
    sim_dir_path: Path | None = None,
    sim_dir_name: str | None = None,
    api_base: str | None = None,
    api_key: str = "",
    species_list: list[str] | None = None,
    force_refresh: bool = False,
) -> dict:
    from backend.services.plot_explanation import sanitize_plot_explanations

    if plot_data.get("explanations") and not force_refresh:
        return sanitize_plot_explanations(plot_data)

    plot_data = dict(plot_data)
    plot_data.pop("explanations", None)
    plot_data.pop("explanation_llm_used", None)

    images = plot_data.get("images") or []
    image_meta = [{"label": _plot_image_label(img)} for img in images]

    try:
        import httpx

        if api_base:
            from backend.services.simulation_api import RemoteSimulationClient

            client = RemoteSimulationClient(api_base, api_key=api_key)
            explained = client.explain_plot(
                sim_dir=sim_dir_name or "example_simulation",
                species=species_list,
                images=image_meta,
                plot_mode="combined",
            )
            plot_data["explanations"] = explained.get("explanations", {})
            plot_data["explanation_llm_used"] = explained.get("explanation_llm_used", False)
            if explained.get("explanation_error"):
                plot_data["explanation_error"] = explained["explanation_error"]
        elif sim_dir_path is not None:
            from backend.services.plot_explanation import attach_plot_explanations
            from backend.services.nautilus import NautilusRunner

            nautilus_runner = NautilusRunner(settings.nautilus)
            plot_data = attach_plot_explanations(
                sim_dir_path,
                plot_data,
                settings.westlake,
                python_exe=nautilus_runner.python_executable(),
            )
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            detail = exc.response.text or str(exc)
        plot_data["explanation_error"] = (
            f"{detail} — update the simulation API (git pull + restart uvicorn) "
            "or ensure example_simulation/res.pickle exists."
        )
    except Exception as exc:
        plot_data["explanation_error"] = str(exc)

    return sanitize_plot_explanations(plot_data)


def show_plot_results(
    plot_data: dict,
    settings,
    api_base: str | None = None,
    *,
    sim_dir_path: Path | None = None,
    sim_dir_name: str | None = None,
    api_key: str = "",
    species_list: list[str] | None = None,
) -> None:
    import base64

    if plot_data.get("simulation_warning"):
        st.warning(plot_data["simulation_warning"])

    if plot_data.get("skipped"):
        st.warning(f"Plot skipped: {plot_data.get('reason')}")
        return
    if plot_data.get("returncode", 1) != 0:
        st.error("Plotting failed")
        st.code(plot_data.get("stderr") or plot_data.get("stdout") or "")
        return

    plot_data = _ensure_plot_images_displayable(
        plot_data, api_base, api_key=api_key
    )
    ctx = st.session_state.get(EVOLUTION_PLOT_CTX)
    if ctx is not None:
        ctx["plot_data"] = _slim_plot_data_for_session(plot_data)

    if plot_data.get("image_load_error"):
        st.error(f"Could not load plot image: {plot_data['image_load_error']}")

    images = plot_data.get("images") or []
    if not images and plot_data.get("image_path"):
        images = [{"label": "plot", "path": plot_data["image_path"]}]

    if not _plot_images_ready(plot_data):
        st.warning(
            "No displayable image in the response. "
            "Redeploy Streamlit, update the simulation API (`git pull` + restart uvicorn), "
            "and ensure `POST /api/simulation/plot` returns `images[].base64`."
        )
        if plot_data.get("stderr"):
            st.code(plot_data["stderr"])
        return

    cols = st.columns(min(3, len(images)) or 1)
    explanation_slots: list[tuple[str, object]] = []
    for idx, img in enumerate(images):
        with cols[idx % len(cols)]:
            label = _plot_image_label(img)
            if img.get("base64"):
                st.image(base64.b64decode(img["base64"]), use_container_width=True)
            else:
                url = img.get("url")
                if url and api_base and url.startswith("/"):
                    url = api_base + url
                if url:
                    st.image(url, use_container_width=True)
                else:
                    path = Path(img.get("path") or "")
                    if not path.exists() and img.get("filename"):
                        out_root = settings.nautilus.outputs_dir
                        if not out_root.is_absolute():
                            from backend.config import ROOT

                            out_root = ROOT / out_root
                        path = out_root / plot_data.get("run_id", "") / img["filename"]
                    if path.exists():
                        st.image(str(path), use_container_width=True)
                    else:
                        st.warning("Image unavailable")

            explanation_slots.append((label, st.empty()))

    explanations = plot_data.get("explanations") or {}
    if plot_data.get("explanation_error"):
        st.warning(f"Plot explanation: {plot_data['explanation_error']}")

    for label, slot in explanation_slots:
        caption_text = explanations.get(label)
        if caption_text:
            with slot:
                _render_plot_explanation(caption_text)


def main() -> None:
    settings, db, agent, nautilus, on_cloud = load_resources()
    api_base, api_key = simulation_api_config()
    admin_run_enabled = simulation_admin_mode_enabled(on_cloud)
    apply_starry_theme()

    render_app_branding()
    if on_cloud:
        st.caption("☁️ Streamlit Cloud")

    sidebar_status(settings, db, nautilus)
    if on_cloud and not api_base:
        if load_simulation_catalog():
            st.sidebar.info("Evolution plots: GitHub precomputed gallery")
        else:
            st.sidebar.warning("No API configured / no precomputed plots")

    tab1, tab2 = st.tabs(["🔬 Molecule Query", "📈 Westlake Evolution"])
    with tab1:
        page_query(agent, db, settings)
    with tab2:
        if api_base:
            page_simulation_remote(api_base, api_key, settings, allow_run_sim=admin_run_enabled)
        elif nautilus is not None:
            page_simulation_local(nautilus, settings, allow_run_sim=admin_run_enabled)
        else:
            page_simulation_unavailable(on_cloud)


if __name__ == "__main__":
    main()
