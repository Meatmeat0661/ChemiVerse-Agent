# Streamlit 版使用与公网部署

主入口：**`streamlit_app.py`**（端口默认 **8501**，与旧 FastAPI 8765 无关）

---

## 1. 本机使用

```powershell
cd C:\Users\ROG\astrochem-agent
pip install -r requirements.txt
```

确认 `config.yaml` 里数据库路径正确，然后：

```powershell
streamlit run streamlit_app.py
```

或双击 **`启动Streamlit-本机.bat`** → 浏览器打开 http://127.0.0.1:8501

---

## 2. 同一 WiFi / 实验室局域网

双击 **`启动Streamlit-局域网.bat`**，或：

```powershell
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

本机查 IP：`ipconfig` → 例如 `192.168.1.100`  
别人访问：**http://192.168.1.100:8501**  
（Windows 防火墙需放行 8501）

---

## 3. 别的网络也能用（公网）

### 方案 A：云服务器（推荐，长期稳定）

1. 租 **Ubuntu** 云服务器（2 核 4G+，若要跑 Westlake 演化）。
2. 上传整个 `astrochem-agent`、`westlake-tutorial`、JSON 数据库到 `/opt/`。
3. 安装依赖并改 `config.yaml` 为 Linux 路径（参考 `config.production.example.yaml`）。
4. 运行：

```bash
cd /opt/astrochem-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 可选: pip install torch && pip install -e /opt/westlake-tutorial/westlake

streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

5. 用 **systemd** 或 **screen/tmux** 保持常驻；前面加 **Nginx + HTTPS + 域名**（与 `DEPLOY.md` 类似，把 `proxy_pass` 改成 `http://127.0.0.1:8501`）。

别人打开：`https://你的域名.com`

### 方案 B：Streamlit Community Cloud（仅查询，不适合 Westlake）

适合 **只查分子/反应**、数据库不太大、能放 GitHub 的场景：

1. 把项目推到 **GitHub 公开仓库**（数据库可放 `data/` 或 LFS）。
2. 打开 https://share.streamlit.io → 用 GitHub 登录 → New app。
3. Main file：`streamlit_app.py`，Advanced 里设置 Secrets 覆盖路径（可选）。
4. Deploy 后得到 `https://xxx.streamlit.app` 链接，发给任何人。

注意：云端 **无法** 使用你本机 `E:\...` 路径；演化模拟也 **跑不了**（无 westlake/算力），除非自建 Docker。

### 方案 C：Cloudflare Tunnel（本机临时公网）

电脑需一直开机：

```powershell
# 终端 1
cd C:\Users\ROG\astrochem-agent
streamlit run streamlit_app.py --server.port 8501
```

```powershell
# 终端 2 — 安装 cloudflared 后
cloudflared tunnel --url http://127.0.0.1:8501
```

会显示临时 `https://xxx.trycloudflare.com`，发给别人即可（链接会变，不适合长期）。

---

## 4. 与旧 FastAPI 版的关系

| 项目 | FastAPI (`run_server.py`) | Streamlit (`streamlit_app.py`) |
|------|---------------------------|--------------------------------|
| 端口 | 8765 | 8501 |
| 分享难度 | 需 Nginx 等 | Streamlit 生态更省事 |
| 功能 | 相同后端逻辑 | 相同 `backend/` 模块 |

两套可并存，一般 **对外分享用 Streamlit** 即可。

---

## 5. 常见问题

**Q：每次都要启动吗？**  
本机：是。公网云服务器：用 systemd 开机自启后不用手动。

**Q：查询很慢？**  
首次加载约 1.3 万条反应会占内存，侧边栏会显示条数；已用 `@st.cache_resource` 缓存。

**Q：演化按钮报错？**  
检查本机/服务器是否 `pip install westlake torch`，且 `config.yaml` 里 `tutorial_root` 正确。
