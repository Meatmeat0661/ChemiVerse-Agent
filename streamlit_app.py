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
    page_title="BIRDS-ARDCA",
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

.plot-explanation-card {
  background: rgba(18, 36, 78, 0.55);
  border: 1.5px solid rgba(154, 216, 255, 0.5);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  margin: 0.5rem 0 0.85rem 0;
  color: #d8e4ff !important;
  font-size: 0.95rem;
  line-height: 1.55;
}

.plot-explanation-card strong {
  color: #eef4ff !important;
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

div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div[data-testid="column"] {
  align-self: stretch;
}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot),
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) {
  gap: 0.75rem !important;
}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) > div[data-testid="column"] {
  flex: 1 1 0 !important;
  width: auto !important;
  min-width: 0 !important;
  align-self: auto !important;
}

div[data-testid="stHorizontalBlock"]:has(.st-key-local_plot) .stButton > button,
div[data-testid="stHorizontalBlock"]:has(.st-key-remote_plot) .stButton > button {
  width: 100% !important;
  white-space: nowrap !important;
  font-size: 1.05rem !important;
  min-height: 3rem !important;
  padding: 0.75rem 1rem !important;
  letter-spacing: 0.02em !important;
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

.stButton > button[kind="secondary"] {
  background: rgba(72, 92, 132, 0.55) !important;
  color: #b8c8f0 !important;
  border: 1px solid rgba(140, 165, 210, 0.45) !important;
  box-shadow: none !important;
}

.stButton > button[kind="secondary"]:hover:not(:disabled) {
  filter: brightness(1.06);
}

.stButton > button:disabled {
  opacity: 0.55 !important;
  cursor: not-allowed !important;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.55rem;
}

.stTabs [data-baseweb="tab"] {
  position: relative;
  height: 3rem;
  padding: 0.5rem 1.2rem;
  font-size: 1.2rem;
  border: 1.4px solid rgba(156, 200, 255, 0.6);
  border-radius: 10px 10px 0 0;
  box-sizing: border-box;
}

.stTabs [data-baseweb="tab"]:hover {
  background: rgba(45, 74, 148, 0.5);
}

.stTabs [aria-selected="true"] {
  border-bottom: none !important;
  background: rgba(45, 74, 148, 0.55);
}

.stTabs [aria-selected="true"]::after {
  content: "";
  position: absolute;
  left: -1.4px;
  right: -1.4px;
  bottom: -1.4px;
  height: 4px;
  background-color: #9ad8ff;
  border-radius: 0 0 8px 8px;
  pointer-events: none;
}

.stTabs [data-baseweb="tab-highlight"] {
  display: none !important;
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

/* Help icon (?) next to checkboxes */
[data-testid="stTooltipIcon"] {
  background: rgba(28, 48, 92, 0.85) !important;
  border: 1.5px solid rgba(154, 180, 220, 0.55) !important;
  border-radius: 50% !important;
  width: 1.15rem !important;
  height: 1.15rem !important;
  min-width: 1.15rem !important;
  min-height: 1.15rem !important;
  padding: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: none !important;
}

[data-testid="stTooltipIcon"] svg {
  display: none !important;
}

[data-testid="stTooltipIcon"]::after {
  content: "?";
  color: #9aa8c8;
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1;
  font-family: Georgia, "Times New Roman", serif;
}

.birds-header {
  margin: 0 0 0.85rem 0;
}

.birds-header-inner {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: flex-start;
  gap: 0.2rem 0.45rem;
  max-width: 100%;
}

.birds-title {
  margin: 0 !important;
  padding: 0 !important;
  font-size: 3.35rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.04em;
  color: #eef4ff !important;
  line-height: 1.05 !important;
  white-space: nowrap;
}

.birds-subtitle {
  margin: 0 0 0.18rem 0 !important;
  padding: 0 !important;
  font-size: 1.65rem !important;
  font-weight: 400 !important;
  line-height: 1.2 !important;
  color: #b8c8f0 !important;
  text-align: left;
  white-space: nowrap;
}

.stCaption, .stMarkdown small {
  color: var(--muted) !important;
}
</style>
        """,
        unsafe_allow_html=True,
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


def _render_simulation_conditions(info: dict | None) -> None:
    if not info:
        return
    if info.get("error"):
        st.caption(f"Physical conditions unavailable: {info['error']}")
        return
    from backend.services.simulation_conditions import conditions_to_markdown

    st.markdown("#### Physical conditions")
    st.info(conditions_to_markdown(info))


def _attach_simulation_conditions(
    plot_data: dict,
    *,
    sim_dir_path: Path | None = None,
    sim_dir_name: str | None = None,
    api_base: str | None = None,
    api_key: str = "",
) -> dict:
    if plot_data.get("simulation_conditions"):
        return plot_data
    info = _load_simulation_conditions(
        sim_dir_path=sim_dir_path,
        sim_dir_name=sim_dir_name,
        api_base=api_base,
        api_key=api_key,
    )
    if info:
        plot_data["simulation_conditions"] = info
    return plot_data


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
    default_species = st.session_state.get(default_species_key, settings.nautilus.default_species)
    sim_dir = settings.nautilus.default_sim_dir
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
    plot_clicked, explain_clicked = _plot_action_buttons("local_plot", "local_explain")

    if plot_clicked:
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
        show_plot_results(
            plot_data,
            settings,
            sim_dir_path=sim_path,
            sim_dir_name=sim_dir,
            species_list=species_list,
        )
        return

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

    if plot_clicked:
        if st.session_state.get("plot_in_progress"):
            st.warning("A plot request is already running. Please wait — do not click Plot again.")
            return
        st.session_state["plot_in_progress"] = True
        plot_data = None
        try:
            species_key = ",".join(species_list) if species_list else "default"
            st.caption(
                f"Species: **{species_key}**. First plot for a new list may take **1–2 minutes**; "
                "the same list is faster next time (cached)."
            )
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

        if plot_data.get("from_cache"):
            st.caption("Plot served from server cache (fast).")
        elif plot_data.get("returncode") == 0:
            st.caption("New plot generated on server (cached for next time).")

        _store_evolution_plot_ctx(
            plot_data,
            sim_dir_name=sim_dir,
            species_list=species_list,
            api_base=api_base,
            api_key=api_key,
        )
        show_plot_results(
            plot_data,
            settings,
            api_base=api_base,
            api_key=api_key,
            sim_dir_name=sim_dir,
            species_list=species_list,
        )
        return

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


def _render_plot_explanation(text: str, *, llm_used: bool) -> None:
    import html

    source = "Westlake LLM" if llm_used else "rule-based summary"
    body = html.escape(text).replace("\n", "<br/>")
    st.markdown(
        f'<div class="plot-explanation-card"><strong>About this plot</strong> '
        f'<span style="opacity:0.75;font-size:0.85em">({source})</span><br/><br/>{body}</div>',
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
) -> dict:
    if plot_data.get("explanations"):
        return plot_data

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

    return plot_data


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

    conditions = plot_data.get("simulation_conditions")
    if not conditions:
        conditions = _load_simulation_conditions(
            sim_dir_path=sim_dir_path,
            sim_dir_name=sim_dir_name,
            api_base=api_base,
            api_key=api_key,
        )
    _render_simulation_conditions(conditions)

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
            st.caption(label)
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
    llm_used = bool(plot_data.get("explanation_llm_used"))

    if plot_data.get("explanation_error"):
        st.warning(f"Plot explanation: {plot_data['explanation_error']}")

    for label, slot in explanation_slots:
        caption_text = explanations.get(label)
        if caption_text:
            with slot:
                _render_plot_explanation(caption_text, llm_used=llm_used)


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
