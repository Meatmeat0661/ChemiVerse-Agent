---
name: astrochem-agent
description: >-
  Operates the astrochem-agent web stack: JSON molecule/reaction databases,
  species lookup by SMILES/key/formula, Westlake OpenAI-compatible LLM summaries,
  and local Nautilus evolution via run_nautilus_network.py. Use when working on
  astrochemistry agents, Westlake, Nautilus networks, molecules.json,
  reactions.json, or C:\Users\ROG\astrochem-agent.
---

# 天体化学 Agent（Astrochem Agent）

## 项目位置

默认根目录：`C:\Users\ROG\astrochem-agent`

## 数据格式

### 分子库 `data/molecules.json`

- 根节点为 **数组**，每项一条分子。
- 主键字段：`key`（如 `CCH`）。
- 检索别名：`smiles`、`normal_formula`、`empirical_formulae`、`name`。
- 物性：`ma`（分子量）、`charge`、`num_rings`、`atoms`、`desorption_energy`。
- 观测：`observations[].source` 与 `observations[].origin`（文献 URL）。

### 反应库 `data/reactions.json`

- 根节点为 **数组**；`key` 形如 `CR;N2>N;N`。
- 物种名 `reactants[].name` / `products[].name` 需与分子库 `key` 或 `empirical_formulae` 对齐。
- `is_special: true` 表示 CR、光子等特殊物种。
- 速率：`params[]` 中 `alpha`, `beta`, `gamma`（KIDA 形式 \(k=\alpha T^\beta e^{-\gamma/T}\)），以及 `temp_min` / `temp_max`。

## 配置

1. 复制 `config.example.yaml` → `config.yaml`。
2. 设置完整 JSON 路径（若不在 `data/`）。
3. **Nautilus / Westlake 物理演化**：

```yaml
nautilus:
  project_root: "C:/path/to/your-westlake-repo"
  script: "run_nautilus_network.py"
  default_sim_dir: "example_simulation"
  python: "python"
```

等价命令行（在 `westlake-tutorial` 根目录执行）：

```bash
python westlake/examples/run_nautilus_network.py --dir=example_simulation --use_evolution
```

输出：`example_simulation/res.pickle`

### 丰度演化图

教程脚本 `westlake-tutorial/scripts/plot.py` 使用 `westlake.load_result` + matplotlib。
本项目封装为 `backend/scripts/plot_westlake.py`，Web 通过 `POST /api/simulation/run`（`plot: true`）或 `POST /api/simulation/plot` 调用。

- 图像输出：`outputs/<run_id>/abundances.png`
- 访问 URL：`GET /api/outputs/<run_id>/abundances.png`
- 默认绘图物种：`CO,CH3OH,CH3OCH3`（须在 Nautilus 网络 `gas_species.in` 中存在）
- **出图方式 `plot_mode`**：
  - `combined`：`abundances.png`（多物种一张图）
  - `separate`：每个物种一张，如 `CO.png`、`CH3OH.png`
  - `both`：合并图 + 各物种单图（默认）

配置示例：

```yaml
nautilus:
  tutorial_root: "E:/大学/学术项目/Agent-ChemiVerse/westlake-tutorial"
  script: "westlake/examples/run_nautilus_network.py"
  default_sim_dir: "example_simulation"
  python: "python"   # 须已 pip install westlake torch
```

4. **Westlake LLM**（可选，OpenAI 兼容本地服务）：

```yaml
westlake:
  base_url: "http://127.0.0.1:8000/v1"
  api_key: "not-needed"
  model: "westlake"
```

未配置 `base_url` 时使用规则摘要，不调用 LLM。

## 启动 Web

```bash
cd C:\Users\ROG\astrochem-agent
pip install -r requirements.txt
python run_server.py
```

浏览器打开：`http://127.0.0.1:8765`

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 库与 Nautilus 是否就绪 |
| POST | `/api/query` | 分子查询 + 反应 + 摘要 |
| GET | `/api/molecules/search?q=` | 自动完成 |
| GET | `/api/simulation/preview` | 预览 Nautilus 命令 |
| POST | `/api/simulation/run` | 执行演化模拟（可选自动绘图） |
| POST | `/api/simulation/plot` | 仅从已有 res.pickle 绘图 |
| GET | `/api/outputs/{run_id}/{filename}` | 获取 PNG 图像 |
| POST | `/api/admin/reload` | 热重载 JSON |

### 查询请求体

```json
{
  "query": "[C]#C",
  "include_reactions": true,
  "use_llm": true
}
```

## Agent 逻辑（维护时遵循）

1. **解析**：`query` → `resolve_molecule_key`（精确 → 别名表 → 大小写不敏感）。
2. **反应**：用 `key`、`normal_formula`、`empirical_formulae` 与反应网络 `name` 求交集。
3. **回答**：优先数据库字段；LLM 仅整理上下文，不得编造速率或观测。
4. **模拟**：仅通过 `NautilusRunner` 子进程调用，不阻塞 UI 时需在前端提示长时间运行。

## 常见修改

| 任务 | 文件 |
|------|------|
| 改检索规则 | `backend/db/resolver.py` |
| 改摘要/提示词 | `backend/services/agent.py`, `westlake_llm.py` |
| 改 Nautilus 参数 | `backend/services/nautilus.py`, `config.yaml` |
| 改页面 | `frontend/index.html`, `app.js`, `styles.css` |

## 替换全量数据库

将用户的 `molecules.json`、`reactions.json` 放入 `data/`（或改 `config.yaml`），调用 `POST /api/admin/reload` 或重启服务。

## 故障排查

- **分子未找到**：检查 `empirical_formulae` 与反应网络物种名是否一致。
- **Nautilus 未就绪**：`nautilus.project_root` 必须包含 `run_nautilus_network.py` 与 `example_simulation`。
- **LLM 失败**：服务回退规则摘要；检查 `westlake.base_url` 与本地模型是否提供 `/v1/chat/completions`。
