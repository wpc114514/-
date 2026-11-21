@echo off
rem 划词翻译 启动脚本
cd /d "%~dp0"

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw main.py
    exit /b
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python main.py
    exit /b
)

echo 未找到 Python，请先到 https://www.python.org/downloads/ 安装（勾选 Add to PATH）。
pause
