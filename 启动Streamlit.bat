@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动 ChemiVerse Streamlit ...
echo 本机地址: http://127.0.0.1:8501
echo 局域网请先把 .streamlit\config.toml 中 address 改为 0.0.0.0
start http://127.0.0.1:8501
streamlit run streamlit_ui/app.py
pause
