@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动 Streamlit: http://127.0.0.1:8501
start http://127.0.0.1:8501
python -m streamlit run streamlit_app.py
pause
