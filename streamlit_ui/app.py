"""AstroChem Agent — Streamlit UI (重写版入口).

功能：
- 分子检索（SMILES / key / 分子式）并展示相关反应
- Westlake Nautilus 演化模拟与丰度出图（本机或远程）
"""

from __future__ import annotations

import asyncio
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


st.set_page_config(
    page_title="天体化学 Agent",
    page_icon="🌌",
    layout="wide",
)


def is_streamlit_cloud() -> bool:
    return os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud"


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
    st.sidebar.header("系统状态")

    mol_ok = settings.data.molecules_path.exists()
    rxn_ok = settings.data.reactions_path.exists()
    st.sidebar.write("分子库", "✅" if mol_ok else "❌")
    st.sidebar.write("反应库", "✅" if rxn_ok else "❌")

    if nautilus is not None:
        st.sidebar.write("Westlake 脚本", "✅" if nautilus.script_path().exists() else "❌")
    else:
        st.sidebar.write("Westlake", "—（云端查询模式）")

    if mol_ok and rxn_ok:
        try:
            st.sidebar.caption(f"已加载 {len(db.molecules)} 种分子 · {len(db.reactions)} 条反应")
        except Exception as exc:
            st.sidebar.warning(f"加载失败: {exc}")

    with st.sidebar.expander("路径配置"):
        lines = [
            f"molecules:\n{settings.data.molecules_path}",
            f"reactions:\n{settings.data.reactions_path}",
        ]
        if nautilus is not None:
            lines.append(f"tutorial:\n{nautilus.tutorial_root()}")
        st.code("\n\n".join(lines), language=None)

    if st.sidebar.button("重新加载数据库"):
        load_resources.clear()
        st.rerun()


def _reaction_table(rows, limit=50):
    # rows 已经是 streamlit 友好的字典结构，这里只做截断与显示
    view = rows[:limit]
    st.dataframe(view, use_container_width=True)
    if len(rows) > limit:
        st.caption(f"另有 {len(rows) - limit} 条未显示")


def _species_list_from_text(text: str) -> list[str]:
    return [s.strip() for s in text.replace("，", ",").split(",") if s.strip()]


def page_molecule_query(agent: AstroChemAgent, db: AstroChemDatabase, settings) -> None:
    st.header("分子查询")
    st.caption("支持 SMILES / 物种 key / 分子式，并展示相关反应")

    examples = ["N2", "CCH", "[C]#C", "CO", "HCN", "NH3", "CH3OH", "H2O"]
    ex_cols = st.columns(len(examples))
    for col, ex in zip(ex_cols, examples):
        if col.button(ex, use_container_width=True):
            st.session_state["molecule_query_input"] = ex

    with st.form("molecule_query_form", clear_on_submit=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input(
                "查询",
                placeholder="例如 N2、 [C]#C 、 CH3OH",
                key="molecule_query_input",
            )
        with col2:
            use_llm = st.checkbox("Westlake LLM", value=False, help="需在 config.yaml 配置 base_url")

        include_reactions = st.checkbox("包含相关反应", value=True)
        submitted = st.form_submit_button("查询", type="primary", disabled=not query.strip())

    if not submitted:
        return

    with st.spinner("检索中…"):
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

    st.success(f"解析为 **{result.resolved_key}**" + (" · LLM 摘要" if result.llm_used else ""))

    m = result.molecule
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("分子量 ma", f"{m.ma}" if m.ma else "—")
    c2.metric("电荷", m.charge if m.charge is not None else "—")
    c3.metric("环数", m.num_rings if m.num_rings is not None else "—")
    c4.metric("原子数", m.num_atoms if m.num_atoms else "—")

    st.subheader("标识与结构")
    st.json(
        {
            "key": m.key,
            "normal_formula": m.normal_formula,
            "smiles": m.smiles,
            "inchi": m.inchi,
            "atoms": m.atoms,
            "empirical_formulae": m.empirical_formulae,
        }
    )

    obs = m.observations or []
    if obs:
        st.subheader(f"观测记录（{len(obs)}）")
        st.dataframe(
            [{"source": o.source, "refs": len(o.origin or [])} for o in obs[:200]],
            use_container_width=True,
        )
        if len(obs) > 200:
            st.caption("仅显示前 200 条观测")

    st.subheader("摘要")
    st.markdown(result.summary)

    # 把分子 key 作为后续出图默认物种
    st.session_state["plot_species"] = result.resolved_key or query.strip()

    if not include_reactions:
        return

    st.subheader("相关反应")
    t1, t2 = st.tabs(
        [f"作为反应物 ({len(result.reactions_as_reactant)})", f"作为产物 ({len(result.reactions_as_product)})"]
    )

    def reaction_to_row(rxn):
        left = " + ".join(f"{s.num}×{s.name}{'†' if s.is_special else ''}" for s in rxn.reactants)
        right = " + ".join(f"{s.num}×{s.name}{'†' if s.is_special else ''}" for s in rxn.products)
        p0 = rxn.params[0] if rxn.params else None
        rate = ""
        if p0 and p0.alpha is not None:
            rate = f"α={p0.alpha} β={p0.beta} γ={p0.gamma}"
        return {
            "key": rxn.key,
            "反应": f"{left} → {right}",
            "类型": rxn.reaction_type or "未知类型",
            "速率": rate,
        }

    with t1:
        rows = [reaction_to_row(rxn) for rxn in result.reactions_as_reactant]
        _reaction_table(rows)

    with t2:
        rows = [reaction_to_row(rxn) for rxn in result.reactions_as_product]
        _reaction_table(rows)


def page_reaction_query(db: AstroChemDatabase) -> None:
    st.header("反应查询")
    st.caption("按 reaction key 精确检索，或通过反应物/产物物种匹配展示列表")

    with st.form("reaction_query_form", clear_on_submit=False):
        key = st.text_input("reaction key（如 `CR;N2>N;N`）", placeholder="可留空")
        species = st.text_input("匹配物种（反应物/产物均可，填分子 key 或别名）", placeholder="可留空")
        submitted = st.form_submit_button("检索", type="primary")

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
        st.warning("请至少填写 reaction key 或物种名")
        return

    if not matched:
        st.info("未找到匹配反应")
        return

    st.success(f"找到 {len(matched)} 条匹配反应")
    for rxn in matched[:50]:
        with st.expander(f"{rxn.key}（{rxn.reaction_type or '未知类型'}）", expanded=False):
            left = " + ".join(f"{s.num}×{s.name}{'†' if s.is_special else ''}" for s in rxn.reactants)
            right = " + ".join(f"{s.num}×{s.name}{'†' if s.is_special else ''}" for s in rxn.products)
            st.write(f"**反应**：{left} → {right}")

            if rxn.params:
                st.subheader("速率参数（节选）")
                st.dataframe(
                    [
                        {
                            "alpha": p.alpha,
                            "beta": p.beta,
                            "gamma": p.gamma,
                            "T范围": f"{p.temp_min}..{p.temp_max}" if p.temp_min is not None else "",
                            "origin": ", ".join(p.origin[:3]) if p.origin else "",
                        }
                        for p in rxn.params[:10]
                    ],
                    use_container_width=True,
                )
            else:
                st.caption("该反应无速率参数记录")

    if len(matched) > 50:
        st.caption("仅展示前 50 条匹配反应")


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


def _simulation_form(settings, default_species_key: str = "plot_species"):
    default_species = st.session_state.get(default_species_key, settings.nautilus.default_species)
    sim_dir = st.text_input("模拟目录", value=settings.nautilus.default_sim_dir)
    species_text = st.text_input(
        "绘图物种（逗号分隔）",
        value=default_species if isinstance(default_species, str) else ",".join([default_species]),
    )
    plot_mode = st.selectbox(
        "出图方式",
        options=["both", "combined", "separate"],
        format_func=lambda x: {
            "both": "合并图 + 每个物种单独一张",
            "combined": "仅一张合并图",
            "separate": "仅每个物种单独一张",
        }[x],
        index=0,
    )
    use_evolution = st.checkbox("使用结构演化 (--use_evolution)", value=True)
    plot_after = st.checkbox("运行后自动绘图", value=True)

    st.info("示例: `N2,NH3,HCN,H2CO` 或 `CO,CH3OH,CH3OCH3`", icon="💡")
    species_list = _species_list_from_text(species_text)
    return sim_dir, species_list, plot_mode, use_evolution, plot_after


def show_plot_results(plot_data: dict, settings, api_base: str | None = None) -> None:
    import base64

    if plot_data.get("skipped"):
        st.warning(f"绘图跳过: {plot_data.get('reason')}")
        return
    if plot_data.get("returncode", 1) != 0:
        st.error("绘图失败")
        st.code(plot_data.get("stderr") or plot_data.get("stdout") or "")
        return

    images = plot_data.get("images") or []
    if not images and plot_data.get("image_path"):
        images = [{"label": "plot", "path": plot_data["image_path"]}]

    st.success(f"共 {len(images)} 张图 · run_id={plot_data.get('run_id')}")
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
                st.warning("图像不可用")


def page_simulation_local(nautilus, settings) -> None:
    st.header("Westlake 化学演化 + 绘图（本机）")
    st.caption("在本机安装 westlake 后直接计算")

    sim_dir, species_list, plot_mode, use_evolution, plot_after = _simulation_form(settings)

    col_a, col_b = st.columns(2)
    with col_a:
        run_sim = st.button("运行模拟", type="primary", key="local_run")
    with col_b:
        plot_only = st.button("仅绘图", key="local_plot")

    if run_sim:
        with st.spinner("Westlake 模拟运行中，可能需要数分钟…"):
            try:
                if plot_after:
                    data = nautilus.run_with_plot(
                        sim_dir=sim_dir or None,
                        use_evolution=use_evolution,
                        species=species_list or None,
                        plot_mode=plot_mode,
                        include_images_base64=True,
                        timeout=3600,
                    )
                else:
                    data = nautilus.run(
                        sim_dir=sim_dir or None,
                        use_evolution=use_evolution,
                        timeout=3600,
                    )
            except Exception as exc:
                st.error(str(exc))
                return

        st.write(f"returncode: **{data['returncode']}**")
        with st.expander("运行日志"):
            st.text(data.get("stdout") or "")
            if data.get("stderr"):
                st.code(data["stderr"])

        if plot_after and data.get("plot"):
            show_plot_results(data["plot"], settings)

    if plot_only:
        with st.spinner("绘图…"):
            try:
                sim_path = nautilus.simulation_dir(sim_dir or None)
                if not (sim_path / "res.pickle").exists():
                    st.error(f"未找到 {sim_path / 'res.pickle'}，请先运行模拟")
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


def page_simulation_remote(api_base: str, api_key: str, settings) -> None:
    from backend.services.simulation_api import RemoteSimulationClient

    st.header("Westlake 化学演化 + 绘图（远程）")
    st.caption(f"计算在服务器执行，访客无需安装 westlake · `{api_base}`")

    client = RemoteSimulationClient(api_base, api_key=api_key)
    sim_dir, species_list, plot_mode, use_evolution, plot_after = _simulation_form(settings)

    col_a, col_b = st.columns(2)
    with col_a:
        run_sim = st.button("运行模拟", type="primary", key="remote_run")
    with col_b:
        plot_only = st.button("仅绘图", key="remote_plot")

    if run_sim:
        with st.spinner("正在请求远程 Westlake 服务（可能数分钟）…"):
            try:
                data = client.run(
                    sim_dir=sim_dir or None,
                    use_evolution=use_evolution,
                    plot=plot_after,
                    plot_mode=plot_mode,
                    species=species_list or None,
                )
            except Exception as exc:
                st.error(f"远程模拟失败: {exc}")
                return

        st.write(f"returncode: **{data.get('returncode')}**")
        with st.expander("运行日志"):
            st.text(data.get("stdout") or "")
            if data.get("stderr"):
                st.code(data["stderr"])

        if plot_after and data.get("plot"):
            show_plot_results(data["plot"], settings, api_base=api_base)

    if plot_only:
        with st.spinner("远程绘图…"):
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

    st.title("天体化学 Agent · ChemiVerse")
    if on_cloud:
        st.caption("☁️ Streamlit Cloud")
    else:
        st.markdown("分子物性 / 反应网络检索 · Westlake 丰度演化可视化")

    sidebar_status(settings, db, nautilus)
    if api_base:
        st.sidebar.success("演化图：远程 Westlake 服务")

    tab1, tab2 = st.tabs(["🔬 分子查询", "📈 Westlake 演化图"])

    with tab1:
        # 分子查询与反应查询用子 tab，满足“查询分子和反应”的需求
        st_tabs = st.tabs(["分子检索", "反应检索"])
        with st_tabs[0]:
            page_molecule_query(agent, db, settings)
        with st_tabs[1]:
            page_reaction_query(db)

    with tab2:
        if api_base:
            page_simulation_remote(api_base, api_key, settings)
        elif nautilus is not None:
            page_simulation_local(nautilus, settings)
        else:
            st.warning("当前无法实时计算演化图：未配置远程 API，也无法在本机运行。")


if __name__ == "__main__":
    main()

