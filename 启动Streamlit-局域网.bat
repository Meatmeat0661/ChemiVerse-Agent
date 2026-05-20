@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 局域网访问: http://本机IP:8501
python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
pause
