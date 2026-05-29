# Westlake 模拟服务器部署（访客不用装 westlake）

访客通过 **Streamlit 网页** 点「运行模拟」，请求发到你这台 **模拟 API 服务器**；  
服务器装好 westlake，算完后把 **PNG 图片（base64）** 返回，访客浏览器直接显示。

```
访客浏览器 (Streamlit Cloud)
        │  HTTPS
        ▼
  streamlit_app.py  ──HTTP──▶  你的模拟服务器 :8765
  （无 westlake）              run_server_prod.py + westlake + torch
                                      │
                                      ▼
                               生成 res.pickle → PNG
```

---

## 第一步：准备一台「模拟服务器」

可以是：

- 实验室 Linux 工作站（有公网 IP 或内网穿透）
- 阿里云 / 腾讯云 VPS（2 核 4G 起，推荐）

上传：

- `astrochem-agent` 项目
- `westlake-tutorial`（含 `example_simulation`）
- 不必上传 ChemiVerse JSON（模拟 API 可不加载大库，但 health 会检查 config）

---

## 第二步：安装 westlake

```bash
cd /opt/astrochem-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-local.txt
pip install -r requirements-westlake-sim.txt
pip install torch
pip install git+https://gitee.com/yqiuu/astro-westlake.git
# 或: pip install -e /opt/westlake-tutorial/westlake
```

---

## 第三步：配置 config.yaml

```yaml
nautilus:
  tutorial_root: "/opt/westlake-tutorial"
  script: "westlake/examples/run_nautilus_network.py"
  default_sim_dir: "example_simulation"
  python: "python3"

server:
  host: "0.0.0.0"
  port: 8765
```

可选：设置 API 密钥（防止陌生人滥用算力）

```bash
export SIMULATION_API_KEY="你的随机长字符串"
```

---

## 第四步：启动模拟 API

```bash
cd /opt/astrochem-agent
source .venv/bin/activate
python run_server_prod.py
```

验证：

```bash
curl http://127.0.0.1:8765/api/health
```

安全组 / 防火墙放行 **8765**（或前面加 Nginx 443 → 8765）。

---

## 第五步：Streamlit Cloud 连接模拟服务器

在 https://share.streamlit.io → 你的 App → **Settings → Secrets**：

```toml
[simulation_api]
base_url = "http://你的公网IP:8765"
api_key = "与 SIMULATION_API_KEY 相同"
```

重新 Deploy 后，打开 Streamlit 链接 → **Westlake 演化图** 标签 → 运行模拟。

访客 **不需要** 安装 westlake；图由你的服务器生成并传回。

---

## 本机联调（Streamlit + 本地 API）

终端 1（模拟 API）：

```powershell
cd C:\Users\ROG\astrochem-agent
$env:SIMULATION_API_KEY="test-key"
python run_server_prod.py
```

终端 2（Streamlit）：

```powershell
$env:SIMULATION_API_URL="http://127.0.0.1:8765"
$env:SIMULATION_API_KEY="test-key"
streamlit run streamlit_app.py
```

---

## 验证「AI 图注」接口

在服务器上（把 `ACTUAL_KEY` 换成 `SIMULATION_API_KEY`）：

```bash
# 路由是否存在（应看到 plot/explain）
curl -s http://127.0.0.1:8765/openapi.json | grep -o 'plot/explain'

# 调用说明接口（必须带 sim_dir，且该目录下已有 res.pickle）
curl -s -X POST "http://127.0.0.1:8765/api/simulation/plot/explain" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ACTUAL_KEY" \
  -d '{"sim_dir":"example_simulation","species":["CO"],"images":[{"label":"combined"}]}'
```

| 响应 `detail` | 含义 | 处理 |
|---------------|------|------|
| `Not Found` | 旧版 API，没有 `/plot/explain` | `git pull` 后重启 uvicorn（见下） |
| `No res.pickle in ...` | 路由正常，但还没跑过模拟 | 先在网页点「Plot」或 `POST /api/simulation/run` 生成 `res.pickle` |
| 含 `explanations` 的 JSON | 正常 | Streamlit 点「AI Explanation」即可 |

更新代码并重启 API：

```bash
cd /opt/astrochem-agent && git pull
source .venv/bin/activate
export SIMULATION_API_KEY="你的密钥"
pkill -f "uvicorn backend.main:app" || true
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8765 >> api.log 2>&1 &
```

然后 **Streamlit Cloud → Redeploy**（客户端会对旧 API 自动回退到 `POST /plot?include_explanations=true`）。

---

## 常见问题

**Q：要不要把 westlake 放到 Streamlit Cloud？**  
**不要。** westlake 只装在模拟服务器；Streamlit 只负责界面和转发请求。

**Q：模拟很慢？**  
正常，一次演化可能数分钟。Streamlit 会显示 spinner，请勿重复点击。

**Q：HTTPS？**  
公网建议 Nginx + SSL 终止，`base_url` 用 `https://sim.yourlab.edu`。

**Q：GitHub 上的 westlake？**  
Gitee: `yqiuu/astro-westlake`；若 GitHub 有镜像，可用 `pip install git+https://github.com/...`。
