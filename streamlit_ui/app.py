"""AstroChem Agent — Streamlit UI."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import streamlit as st

# 让 `backend/*` 可被导入（无论从哪里启动 streamlit）
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_settings
from backend.db.loader import AstroChemDatabase
from backend.services.agent import AstroChemAgent
from backend.services.reaction_display import reaction_table_rows


st.set_page_config(
    page_title="Astrochem Agent",
    page_icon="🌌",
    layout="wide",
)


def apply_starry_theme() -> None:
    st.markdown(
        """
<style>
:root {
  --bg-start: #11284f;
  --bg-mid: #27456f;
  --bg-end: #344f79;
  --card: rgba(24, 44, 96, 0.68);
  --card-border: rgba(148, 184, 255, 0.35);
  --text: #e8eeff;
  --muted: #b8c8f0;
  --accent: #6ea6ff;
  --accent-2: #8a7bff;
  --primary-color: #9ad8ff;
}

.stApp {
  color: var(--text);
  background:
    radial-gradient(ellipse 58% 42% at -4% 104%, rgba(222, 239, 255, 0.52), transparent 66%),
    radial-gradient(ellipse 65% 48% at 12% 88%, rgba(173, 208, 245, 0.26), transparent 72%),
    radial-gradient(ellipse 92% 70% at 50% -18%, rgba(104, 148, 210, 0.17), transparent 74%),
    radial-gradient(1.7px 1.7px at 9% 17%, rgba(255,255,255,0.72), transparent 62%),
    radial-gradient(1.4px 1.4px at 21% 35%, rgba(236,245,255,0.62), transparent 62%),
    radial-gradient(1.6px 1.6px at 33% 13%, rgba(241,248,255,0.66), transparent 62%),
    radial-gradient(1.3px 1.3px at 48% 28%, rgba(232,242,255,0.58), transparent 62%),
    radial-gradient(1.5px 1.5px at 62% 18%, rgba(244,250,255,0.64), transparent 62%),
    radial-gradient(1.3px 1.3px at 79% 30%, rgba(230,242,255,0.56), transparent 62%),
    radial-gradient(1.4px 1.4px at 87% 14%, rgba(250,252,255,0.67), transparent 62%),
    radial-gradient(1.2px 1.2px at 74% 58%, rgba(233,244,255,0.48), transparent 62%),
    radial-gradient(1.1px 1.1px at 56% 72%, rgba(224,238,255,0.42), transparent 62%),
    radial-gradient(1.1px 1.1px at 41% 60%, rgba(236,246,255,0.44), transparent 62%),
    linear-gradient(166deg, var(--bg-start) 0%, var(--bg-mid) 54%, var(--bg-end) 100%);
  background-attachment: fixed;
}

[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section.main > div {
  background: transparent;
}

h1, h2, h3, h4, h5, h6, p, label, span, li, div {
  color: var(--text);
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(14, 32, 72, 0.92) 0%, rgba(18, 42, 88, 0.88) 100%);
  border-right: 1px solid rgba(148, 184, 255, 0.28);
}

[data-testid="stForm"], .stAlert, [data-testid="stExpander"] {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
}

/* Query tables & evolution plot images */
[data-testid="stDataFrame"],
.stDataFrame {
  background: rgba(18, 36, 78, 0.55) !important;
  border: 1.5px solid rgba(154, 216, 255, 0.58) !important;
  border-radius: 12px !important;
  padding: 0.4rem !important;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(48, 82, 160, 0.22);
}

[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
[data-testid="stDataFrame"] [data-testid="glideDataEditor"] {
  border-radius: 8px;
}

[data-testid="stImage"] {
  background: rgba(18, 36, 78, 0.45);
  border: 1.5px solid rgba(154, 216, 255, 0.58) !important;
  border-radius: 12px;
  padding: 0.55rem;
  box-sizing: border-box;
  box-shadow: 0 4px 16px rgba(48, 82, 160, 0.2);
}

[data-testid="stImage"] img {
  border-radius: 8px;
  border: 1px solid rgba(154, 216, 255, 0.38);
  display: block;
  width: 100%;
}

[data-testid="stMetric"] {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  box-sizing: border-box;
  padding: 0.9rem 1.1rem 1rem !important;
  min-height: 5.6rem;
  overflow: visible;
}

[data-testid="stMetricLabel"] {
  padding: 0 !important;
  margin: 0 0 0.45rem 0 !important;
  line-height: 1.35 !important;
  white-space: normal;
}

[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] div {
  padding: 0 !important;
  margin: 0 !important;
}

[data-testid="stMetricValue"] {
  padding: 0 !important;
  margin: 0 !important;
  line-height: 1.15 !important;
}

[data-testid="stMetricValue"] div {
  padding: 0 !important;
  margin: 0 !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
  align-self: stretch;
}

[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
textarea {
  background: rgba(34, 56, 112, 0.88) !important;
  color: var(--text) !important;
  border: 1px solid rgba(156, 186, 255, 0.6) !important;
}

.stTextInput input, .stTextArea textarea {
  color: var(--text) !important;
}

.stButton > button {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #f8fbff;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(85, 118, 214, 0.32);
}

.stButton > button[kind="primary"] {
  padding: 0.95rem 2.3rem !important;
  min-height: 3.25rem;
  font-size: 1.36rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  border-radius: 12px;
}

.stButton > button:hover {
  filter: brightness(1.08);
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.55rem;
}

.stTabs [data-baseweb="tab"] {
  height: 3rem;
  padding: 0.5rem 1.2rem;
  font-size: 1.2rem;
  border: 1.4px solid rgba(156, 200, 255, 0.6);
  border-radius: 10px 10px 0 0;
}

.stTabs [data-baseweb="tab"]:hover {
  background: rgba(45, 74, 148, 0.5);
}

.stTabs [aria-selected="true"] {
  border-bottom: none !important;
  background: rgba(45, 74, 148, 0.55);
}

/* Streamlit default tab indicator (orange) */
.stTabs [data-baseweb="tab-highlight"] {
  background-color: #9ad8ff !important;
  height: 4px !important;
}

.stTabs [data-baseweb="tab-border"] {
  display: none !important;
}

/* Checkboxes: replace Streamlit orange with blue */
[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:first-child {
  background: rgba(34, 56, 112, 0.65) !important;
  border-color: rgba(154, 216, 255, 0.85) !important;
}

[data-testid="stCheckbox"] label[data-baseweb="checkbox"][aria-checked="true"] > div:first-child {
  background: linear-gradient(135deg, #5b9aff, #7a8dff) !important;
  border-color: #9ad8ff !important;
}

[data-testid="stCheckbox"] svg {
  fill: #f8fbff !important;
}

.stCaption, .stMarkdown small {
  color: var(--muted) !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def is_streamlit_cloud() -> bool:
    if os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud":
        return True
    # Streamlit Cloud 工作目录通常为 /mount/src/...
    return Path.cwd().as_posix().startswith("/mount/src")


def _apply_secrets_to_settings(settings):
    """把 Streamlit Cloud 的 secrets 映射到 settings。"""
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
    root = Path(__file__).resolve().parents[1]
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


def _reaction_table(rows) -> None:
    st.caption(f"{len(rows)} rows (including multiple rate sources)")
    st.dataframe(rows, use_container_width=True)


def _species_list_from_text(text: str) -> list[str]:
    return [s.strip() for s in text.replace("，", ",").split(",") if s.strip()]


def _plot_action_button(key: str) -> bool:
    return st.button("Plot", type="primary", key=key)


def page_molecule_query(agent: AstroChemAgent, db: AstroChemDatabase, settings) -> None:
    st.header("Molecule Query")
    st.caption("Supports SMILES / species key / formula, with linked reactions.")

    examples = ["N2", "CCH", "[C]#C", "CO", "HCN", "NH3", "CH3OH", "H2O"]
    ex_cols = st.columns(len(examples))
    for col, ex in zip(ex_cols, examples):
        if col.button(ex, use_container_width=True):
            st.session_state["molecule_query_input"] = ex

    with st.form("molecule_query_form", clear_on_submit=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input(
                "Query",
                placeholder="e.g., N2, [C]#C, CH3OH",
                key="molecule_query_input",
            )
        with col2:
            use_llm = st.checkbox("Westlake LLM", value=False, help="Requires westlake.base_url in config.yaml")

        include_reactions = st.checkbox("Include related reactions", value=True)
        submitted = st.form_submit_button("Search", type="primary", disabled=not query.strip())

    if not submitted:
        return

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

    # 把分子 key 作为后续出图默认物种
    st.session_state["plot_species"] = result.resolved_key or query.strip()

    if not include_reactions:
        return

    st.subheader("Related Reactions")
    t1, t2 = st.tabs(
        [f"As Reactant ({len(result.reactions_as_reactant)})", f"As Product ({len(result.reactions_as_product)})"]
    )

    def rows_for_reactions(reactions):
        rows: list[dict] = []
        for rxn in reactions:
            rows.extend(reaction_table_rows(rxn))
        return rows

    st.caption("If a reaction has multiple literature/database rate sets, each appears in a separate row (source, α/β/γ, temperature range).")

    with t1:
        _reaction_table(rows_for_reactions(result.reactions_as_reactant))

    with t2:
        _reaction_table(rows_for_reactions(result.reactions_as_product))


def page_reaction_query(db: AstroChemDatabase) -> None:
    st.header("Reaction Query")
    st.caption("Search exactly by reaction key, or match by reactant/product species.")

    with st.form("reaction_query_form", clear_on_submit=False):
        key = st.text_input("Reaction key (e.g., `CR;N2>N;N`)", placeholder="Optional")
        species = st.text_input("Match species (reactant/product; key or alias)", placeholder="Optional")
        submitted = st.form_submit_button("Search", type="primary")

    if not submitted:
        return

    key = (key or "").strip()
    species = (species or "").strip()

    matched = []
    if key:
        matched = [r for r in db.reactions if r.key == key]
    elif species:
        # db.reactions 里 ReactionSpecies.name 是网络物种名；这里用 resolver 的别名规则比较麻烦，
        # 直接做 case-insensitive 文本匹配，且同时匹配 reactants/products 的 name
        low = species.lower()
        for r in db.reactions:
            reactant_names = {s.name.lower() for s in r.reactants}
            product_names = {s.name.lower() for s in r.products}
            if low in reactant_names or low in product_names:
                matched.append(r)
    else:
        st.warning("Please provide either a reaction key or a species name.")
        return

    if not matched:
        st.info("No matching reactions found.")
        return

    st.success(f"Found {len(matched)} matching reactions")
    rows: list[dict] = []
    for rxn in matched:
        rows.extend(reaction_table_rows(rxn))
    st.caption("Multiple rate sources for the same reaction are shown as separate rows.")
    _reaction_table(rows)


def simulation_api_config() -> tuple[str | None, str]:
    # Streamlit Cloud secrets 优先；本地走环境变量
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
    """Cloud 默认关闭实时模拟；管理员输入密钥后开启。"""
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
    token = st.sidebar.text_input("Simulation admin key", type="password", key="sim_admin_key")
    enabled = token.strip() == admin_key
    if enabled:
        st.sidebar.success("Real-time simulation enabled (admin)")
    return enabled


def _simulation_form(settings, default_species_key: str = "plot_species"):
    default_species = st.session_state.get(default_species_key, settings.nautilus.default_species)
    sim_dir = settings.nautilus.default_sim_dir
    species_text = st.text_input(
        "Species to plot (comma-separated)",
        value=default_species if isinstance(default_species, str) else ",".join([default_species]),
    )
    # 固定仅输出一张合并图，简化访客操作
    plot_mode = "combined"
    use_evolution = True
    plot_after = True

    st.info("Examples: `N2,NH3,HCN,H2CO` or `CO,CH3OH,CH3OCH3`", icon="💡")
    species_list = _species_list_from_text(species_text)
    return sim_dir, species_list, plot_mode, use_evolution, plot_after


def load_simulation_catalog() -> list[dict]:
    path = ROOT / "data" / "simulation_catalog.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def page_simulation_static() -> None:
    st.header("Westlake Evolution Plots (Precomputed)")
    st.caption("Displays plots committed to the repository; no local or Cloud westlake install required.")
    catalog = load_simulation_catalog()
    if not catalog:
        st.warning("No precomputed plots found. Maintainers can run `python scripts/publish_plots_to_repo.py --help` locally.")
        return

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
        path = ROOT / img["file"]
        with cols[idx % len(cols)]:
            st.caption(img.get("label", path.name))
            if path.exists():
                st.image(str(path), use_container_width=True)
            else:
                st.warning(f"Missing: {img['file']}")


def page_simulation_unavailable() -> None:
    catalog = load_simulation_catalog()
    if catalog:
        page_simulation_static()
        return

    st.header("Westlake Evolution")
    st.warning("Streamlit Cloud cannot run westlake simulations directly.")
    st.markdown(
        """
**Available options:**

1. **Precomputed plots**: generate PNG files locally and push to GitHub (see `NO_SERVER_PLOTS.md`)  
2. **Remote simulation API**: configure `simulation_api.base_url` in Secrets (see `DEPLOY_SIMULATION_SERVER.md`)  
3. **Run locally**: `streamlit run streamlit_ui/app.py` with `nautilus.tutorial_root` configured in `config.yaml`
        """
    )


def _show_simulation_preflight(nautilus, sim_dir: str | None) -> dict[str, object]:
    status = nautilus.environment_status(sim_dir)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Simulation Env", "✅" if status["simulation_ready"] else "❌")
    c2.metric("res.pickle", "✅" if status["pickle_ok"] else "❌")
    c3.metric("Plot Dependencies", "✅" if status["plot_deps_ok"] else "❌")
    c4.metric("Simulation Directory", "✅" if status["sim_dir_ok"] else "❌")

    with st.expander("Environment Details"):
        st.code(
            f"Simulation Python: {status['sim_python']}\n"
            f"Plot Python: {status['plot_python']}\n"
            f"Simulation directory: {status['sim_dir']}\n"
            f"Result file: {status['pickle_path']}",
            language=None,
        )
        if not status["westlake_ok"]:
            st.error(f"Simulation Python cannot import westlake: {status['westlake_error']}")
            st.caption("Run: `powershell .\\scripts\\setup_westlake_local.ps1`")
        elif not status["numpy_ok"]:
            st.error(f"Incompatible numpy version: {status['numpy_info']}")
            st.code(
                f'"{status["sim_python"]}" -m pip install "numpy<2"',
                language="powershell",
            )
        if not status["plot_deps_ok"]:
            st.error(f"Plot Python is missing dependencies: {status['plot_deps_error']}")
            st.caption("In the Streamlit runtime environment, run: `pip install matplotlib westlake`")

    if status["pickle_ok"] and status["plot_deps_ok"]:
        st.info("Use **Plot Only** for fast rendering from existing results.")
    elif not status["simulation_ready"]:
        st.warning("Simulation environment is not ready; only plotting from existing `res.pickle` is available.")

    return status


def show_plot_results(plot_data: dict, settings, api_base: str | None = None) -> None:
    import base64

    if plot_data.get("simulation_warning"):
        st.warning(plot_data["simulation_warning"])

    if plot_data.get("skipped"):
        st.warning(f"Plot skipped: {plot_data.get('reason')}")
        if plot_data.get("stderr"):
            st.code(plot_data["stderr"])
        st.caption("If `example_simulation/res.pickle` exists, try **Plot Only**.")
        return
    if plot_data.get("returncode", 1) != 0:
        st.error("Plotting failed")
        st.code(plot_data.get("stderr") or plot_data.get("stdout") or "")
        return

    images = plot_data.get("images") or []
    if not images and plot_data.get("image_path"):
        images = [{"label": "plot", "path": plot_data["image_path"]}]

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

            from pathlib import Path as _Path

            path = _Path(img.get("path") or "")
            if not path.exists() and img.get("filename"):
                out_root = settings.nautilus.outputs_dir
                if not out_root.is_absolute():
                    out_root = ROOT / out_root
                path = out_root / plot_data.get("run_id", "") / img["filename"]

            if path.exists():
                st.image(str(path), use_container_width=True)
            else:
                st.warning("Image unavailable")


def page_simulation_local(nautilus, settings, allow_run_sim: bool = True) -> None:
    st.header("Westlake Evolution + Plotting (Local)")
    st.caption("Runs directly on a local westlake installation.")

    sim_dir, species_list, plot_mode, use_evolution, plot_after = _simulation_form(settings)
    _show_simulation_preflight(nautilus, sim_dir or None)

    plot_only = _plot_action_button("local_plot")

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

    st.header("Westlake Evolution + Plotting")

    client = RemoteSimulationClient(api_base, api_key=api_key)
    sim_dir, species_list, plot_mode, use_evolution, plot_after = _simulation_form(settings)

    plot_only = _plot_action_button("remote_plot")

    if plot_only:
        with st.spinner("Plotting..."):
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


def main() -> None:
    settings, db, agent, nautilus, on_cloud = load_resources()
    api_base, api_key = simulation_api_config()
    admin_run_enabled = simulation_admin_mode_enabled(on_cloud)
    apply_starry_theme()

    st.title("Astrochem Agent · ChemiVerse")
    if on_cloud:
        st.caption("☁️ Streamlit Cloud")
    else:
        st.markdown("Molecular properties / reaction network lookup · Westlake abundance evolution visualization")

    sidebar_status(settings, db, nautilus)

    tab1, tab2 = st.tabs(["🔬 Molecule Query", "📈 Westlake Evolution"])

    with tab1:
        # 分子查询与反应查询用子 tab，满足“查询分子和反应”的需求
        st_tabs = st.tabs(["Molecule Search", "Reaction Search"])
        with st_tabs[0]:
            page_molecule_query(agent, db, settings)
        with st_tabs[1]:
            page_reaction_query(db)

    with tab2:
        catalog = load_simulation_catalog()
        use_precomputed = is_streamlit_cloud() or (
            catalog and (nautilus is None or not nautilus.script_path().exists())
        )
        if api_base and not use_precomputed:
            page_simulation_remote(api_base, api_key, settings, allow_run_sim=admin_run_enabled)
        elif use_precomputed:
            page_simulation_unavailable()
        elif nautilus is not None:
            page_simulation_local(nautilus, settings, allow_run_sim=admin_run_enabled)
        else:
            page_simulation_unavailable()


if __name__ == "__main__":
    main()

