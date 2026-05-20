# 天体化学 Agent

基于 JSON 分子库与反应库的 Web 智能体：输入 SMILES / 物种 key / 分子式，返回物性、观测与相关反应；可调用本地 Westlake Nautilus 运行物理演化。

## 快速开始（Streamlit）

```bash
cd C:\Users\ROG\astrochem-agent
pip install -r requirements.txt
streamlit run streamlit_app.py
```

打开 http://127.0.0.1:8501 ，或双击 `启动Streamlit-本机.bat`。

**别的网络的人也能用**：

- **Streamlit Cloud（推荐，免服务器）**：按 [STREAMLIT_CLOUD.md](STREAMLIT_CLOUD.md) 推到 GitHub 一键部署  
- 自建服务器 / 隧道：见 [STREAMLIT.md](STREAMLIT.md)

## FastAPI 版（可选）

```bash
python run_server.py
```

打开 http://127.0.0.1:8765

## 接入你的数据

1. 将完整 `molecules.json`、`reactions.json` 放到 `data/`（或修改 `config.yaml` 中的路径）。
2. 确保反应网络中的 `name` 与分子 `key` / `empirical_formulae` 一致。

## Westlake / Nautilus

在 `config.yaml` 中设置：

```yaml
nautilus:
  project_root: "C:/path/to/westlake"
  script: "run_nautilus_network.py"
  default_sim_dir: "example_simulation"
```

网页「Nautilus 演化模拟」等价于：

```bash
python run_nautilus_network.py --dir=<sim_dir> --use_evolution
```

## Cursor Skill

项目 skill 位于 `.cursor/skills/astrochem-agent/SKILL.md`，在 Cursor 中开发本项目时会自动加载领域说明。

## 结构

```
astrochem-agent/
├── streamlit_app.py  # Streamlit 主界面（推荐）
├── backend/          # 检索 + Agent + Westlake
├── frontend/         # 旧版静态 Web UI
├── data/             # 示例 JSON（请替换为全量库）
├── config.example.yaml
└── run_server.py
```
