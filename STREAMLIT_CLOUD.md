# Streamlit Community Cloud 部署（公网链接）

**重要：**

- **查分子/反应**：只需 JSON，访客不用装 westlake。
- **演化图**：访客也不用装 westlake —— 需另有一台 **模拟 API 服务器**（见 [DEPLOY_SIMULATION_SERVER.md](DEPLOY_SIMULATION_SERVER.md)），在 Streamlit Secrets 里配置 `simulation_api.base_url`。

部署完成后链接示例：`https://astrochem-agent-xxxx.streamlit.app`

---

## 前提

1. [GitHub](https://github.com) 账号  
2. 仓库需 **Public（公开）**（免费版 Streamlit Cloud 要求；私有库需付费计划）  
3. 数据库两个 JSON 合计约 **21 MB**，可放进 GitHub（单文件 < 100 MB）

---

## 第一步：准备仓库

在项目根目录 `astrochem-agent` 执行：

### 1. 复制数据库到 `data/`

```powershell
cd C:\Users\ROG\astrochem-agent
python scripts/prepare_streamlit_cloud.py
```

确认存在：

- `data/chemiverse_species.json`
- `data/chemiverse_reactions.json`

### 2. 初始化 Git 并推送（若尚未有远程仓库）

```powershell
git init
git add .
git commit -m "Add Streamlit app for ChemiVerse"
```

在 GitHub 网页 **New repository** 创建仓库（例如 `astrochem-agent`），然后：

```powershell
git remote add origin https://github.com/你的用户名/astrochem-agent.git
git branch -M main
git push -u origin main
```

**不要** 把含个人路径的 `config.yaml` 推上去（已在 `.gitignore`）；云端会用 `config.cloud.yaml`。

---

## 第二步：在 Streamlit Cloud 创建应用

1. 打开 https://share.streamlit.io ，用 GitHub 登录  
2. 点击 **Create app**  
3. 填写：
   - **Repository**：`你的用户名/astrochem-agent`
   - **Branch**：`main`
   - **Main file path**：`streamlit_app.py`
4. **Advanced settings**（可选）：
   - Python version：3.11 或 3.12
   - Secrets：一般可不填；若自定义路径，粘贴 `.streamlit/secrets.toml.example` 内容  
5. 点击 **Deploy**

首次构建约 2～5 分钟。成功后右上角有 **Open app**。

---

## 第三步：发给别人

把 Streamlit 给的 URL 直接分享，例如：

```text
https://astrochem-agent-xxxxx.streamlit.app
```

对方浏览器打开即可，输入 `N2`、`CCH`、`[C]#C` 等查询。

---

## 更新应用

本地改代码或更新 JSON 后：

```powershell
git add .
git commit -m "update"
git push
```

Streamlit Cloud 会自动重新部署（可在控制台看 Logs）。

---

## 常见问题

### 构建失败 `FileNotFoundError` 数据库

未把 `data/chemiverse_*.json` 提交到 GitHub。运行 `prepare_streamlit_cloud.ps1` 后 `git add data/` 再 push。

### 构建很慢 / 内存不足

反应库约 1.3 万条，首次加载需几十秒；若 Cloud 重启，冷启动会再加载一次。属正常。

### 想隐藏 Westlake 页

云端已自动隐藏演化功能，仅显示分子查询。

### 私有仓库

免费 Streamlit Cloud 通常要求 **公开仓库**。若必须私有，考虑：
- 云服务器自建 `streamlit run`（见 `STREAMLIT.md`）
- 或 Streamlit Teams 付费计划

### 数据库太大（未来超过 100 MB）

使用 [Git LFS](https://git-lfs.github.com/) 跟踪 `data/*.json`，或在 Secrets 里改为从 URL 下载（需自行改 `streamlit_app.py` 启动逻辑）。

---

## 检查清单

- [ ] `data/chemiverse_species.json` 已提交  
- [ ] `data/chemiverse_reactions.json` 已提交  
- [ ] `streamlit_app.py` 在仓库根目录  
- [ ] `requirements.txt` 含 `streamlit`  
- [ ] `config.cloud.yaml` 已提交  
- [ ] 未提交本地 `config.yaml`（含 E: 盘路径）
