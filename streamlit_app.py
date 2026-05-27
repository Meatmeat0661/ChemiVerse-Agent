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

st.set_page_config(
    page_title="Astrochem Agent",
    page_icon="🌌",
    layout="wide",
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

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Query",
            placeholder="e.g., N2, [C]#C, CH3OH",
            key="query_input",
        )
    with col2:
        use_llm = st.checkbox("Westlake LLM", value=False, help="Requires westlake.base_url in config.yaml")

    include_reactions = st.checkbox("Include related reactions", value=True)

    if st.button("Search", type="primary", disabled=not query.strip()):
        with st.spinner("Searching..."):
            result = run_async(
                agent.answer(
                    query.strip(),
                    include_reactions=include_reactions,
                    use_llm=use_llm,
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


def _simulation_form(settings, default_species_key: str = "plot_species"):
    default_species = st.session_state.get(default_species_key, settings.nautilus.default_species)
    sim_dir = settings.nautilus.default_sim_dir
    st.caption(f"Simulation directory is fixed: `{sim_dir}`")
    species_text = st.text_input(
        "Species to plot (comma-separated)",
        value=default_species if isinstance(default_species, str) else ",".join([default_species]),
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
    plot_only = st.button("Plot Only", type="primary", key="local_plot")
    st.info("Run Simulation is hidden; plotting uses existing result files only.")

    if plot_only:
        with st.spinner("Plotting..."):
            try:
                sim_path = nautilus.simulation_dir(sim_dir or None)
                if not (sim_path / "res.pickle").exists():
                    st.error(f"{sim_path / 'res.pickle'} not found. Please generate simulation results first.")
                    return
                plot_data = nautilus.plotter.plot(
                    sim_dir=sim_path,
                    species=species_list or None,
                    mode=plot_mode,
                    include_images_base64=True,
                )
            except Exception as exc:
                st.error(str(exc))
                return
        show_plot_results(plot_data, settings)


def page_simulation_remote(api_base: str, api_key: str, settings, allow_run_sim: bool = True) -> None:
    from backend.services.simulation_api import RemoteSimulationClient

    st.header("Westlake Evolution + Plotting (Remote)")
    st.caption(f"Computation runs on the server; visitors do not need local westlake · `{api_base}`")

    client = RemoteSimulationClient(api_base, api_key=api_key)
    sim_dir, species_list, plot_mode, use_evolution, plot_after = _simulation_form(settings)
    plot_only = st.button("Plot Only", type="primary", key="remote_plot")
    st.info("Run Simulation is hidden; visitors can only plot from existing results.")

    if plot_only:
        with st.spinner("Remote plotting..."):
            try:
                plot_data = client.plot_only(
                    sim_dir=sim_dir or None,
                    plot_mode=plot_mode,
                    species=species_list or None,
                )
            except Exception as exc:
                st.error(str(exc))
                return
        show_plot_results(plot_data, settings, api_base=api_base)


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


def show_plot_results(plot_data: dict, settings, api_base: str | None = None) -> None:
    import base64

    if plot_data.get("skipped"):
        st.warning(f"Plot skipped: {plot_data.get('reason')}")
        return
    if plot_data.get("returncode", 1) != 0:
        st.error("Plotting failed")
        st.code(plot_data.get("stderr") or plot_data.get("stdout") or "")
        return

    images = plot_data.get("images") or []
    if not images and plot_data.get("image_path"):
        images = [{"label": "plot", "path": plot_data["image_path"]}]

    st.success(f"{len(images)} image(s) · run_id={plot_data.get('run_id')}")
    cols = st.columns(min(3, len(images)) or 1)
    for idx, img in enumerate(images):
        with cols[idx % len(cols)]:
            st.caption(img.get("label") or img.get("filename") or "plot")
            if img.get("base64"):
                st.image(base64.b64decode(img["base64"]), use_container_width=True)
                continue
            url = img.get("url")
            if url and api_base and url.startswith("/"):
                url = api_base + url
            if url:
                st.image(url, use_container_width=True)
                continue
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


def main() -> None:
    settings, db, agent, nautilus, on_cloud = load_resources()
    api_base, api_key = simulation_api_config()
    admin_run_enabled = simulation_admin_mode_enabled(on_cloud)

    st.title("Astrochem Agent · ChemiVerse")
    if on_cloud:
        st.caption("☁️ Streamlit Cloud")
    else:
        st.markdown("Molecular property lookup / reaction network search · Westlake abundance evolution visualization")

    sidebar_status(settings, db, nautilus)
    if api_base:
        st.sidebar.success("Evolution plots: Remote Westlake service")
    elif on_cloud:
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
