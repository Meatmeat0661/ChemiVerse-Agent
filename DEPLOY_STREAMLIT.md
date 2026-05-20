# Streamlit 版：本机、局域网、公网访问

入口文件：**`streamlit_app.py`**

---

## 1. 本机使用（你自己）

```powershell
cd C:\Users\ROG\astrochem-agent
pip install -r requirements.txt
streamlit run streamlit_app.py
```

或双击 **`启动Streamlit.bat`**。

浏览器自动打开：**http://127.0.0.1:8501**

> 关掉运行 Streamlit 的黑色窗口 = 网站关闭。

---

## 2. 同一 WiFi / 实验室局域网（别人连你的电脑）

### 步骤

1. 编辑 `.streamlit/config.toml`：

```toml
[server]
address = "0.0.0.0"
port = 8501
```

2. 启动：

```powershell
streamlit run streamlit_app.py
```

3. 查你电脑的局域网 IP：

```powershell
ipconfig
```

例如 `192.168.1.100`。

4. **别人**浏览器打开：

```text
http://192.168.1.100:8501
```

5. Windows 防火墙：允许 **8501** 端口入站（专用网络）。

### 注意

- 你的电脑要一直开着并运行 Streamlit。
- 数据库和 Westlake 都在你这台机器上算。

---

## 3. 别的网络的人也能用（公网）

任选其一：

### 方案 A：云服务器（推荐、稳定）

1. 租 **Ubuntu** 云服务器（2 核 4G+，要跑演化建议更大）。
2. 上传整个 `astrochem-agent`、JSON 数据库、`westlake-tutorial`（可选）。
3. 服务器上：

```bash
cd /opt/astrochem-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 可选：pip install torch && pip install -e /opt/westlake-tutorial/westlake
cp config.production.example.yaml config.yaml
# 编辑 config.yaml 路径
```

4. `.streamlit/config.toml` 设 `address = "0.0.0.0"`。

5. 常驻运行（systemd 示例）：

```ini
# /etc/systemd/system/astrochem-streamlit.service
[Service]
WorkingDirectory=/opt/astrochem-agent
ExecStart=/opt/astrochem-agent/.venv/bin/streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
```

```bash
sudo systemctl enable --now astrochem-streamlit
```

6. 安全组放行 **8501**，或用 **Nginx** 反代到 80/443 + 域名。

别人访问：`http://服务器公网IP:8501` 或 `https://你的域名`

---

### 方案 B：Streamlit Community Cloud（仅查询功能）

适合 **只查分子/反应**、不在云端跑 Westlake 演化（Cloud 装不了你的 westlake 大依赖）。

1. 把项目推到 **GitHub**（不要提交 `config.yaml` 和超大私密数据；可用 Git LFS 或只放小样本）。
2. 打开 https://share.streamlit.io ，用 GitHub 登录。
3. New app → 选仓库 → Main file：`streamlit_app.py`
4. 在 Secrets 里配置数据路径或把 JSON 放进仓库 `data/`。

限制：无法直接调用你本机 Westlake；演化仍需云服务器方案 A。

---

### 方案 C：Cloudflare Tunnel（本机临时公网）

电脑长期开机，把本机 8501 暴露为 HTTPS 公网地址。步骤见 `DEPLOY.md` 方案 B，把端口改为 **8501**、`service: http://127.0.0.1:8501`。

---

## 4. 和旧版 FastAPI 的关系

| 版本 | 启动命令 | 默认端口 |
|------|----------|----------|
| Streamlit（新） | `streamlit run streamlit_app.py` | 8501 |
| FastAPI（旧） | `python run_server.py` | 8765 |

可以只保留 Streamlit；FastAPI 仍可用于 API 集成。

---

## 5. 安全提醒

公网开放前建议：

- 加学校 VPN / 密码（Nginx `auth_basic` 或 Streamlit-Authenticator）
- 限制 Westlake 演化按钮的使用（耗 CPU）
