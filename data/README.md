# 数据库文件（Streamlit Cloud 必需）

部署到 Streamlit Cloud 前，将 ChemiVerse JSON 复制到此目录：

- `chemiverse_species.json`（约 0.8 MB）
- `chemiverse_reactions.json`（约 20 MB）

Windows 一键复制（在项目根目录 PowerShell）：

```powershell
python scripts/prepare_streamlit_cloud.py
```

然后 `git add data/chemiverse_*.json` 并推送到 GitHub。
