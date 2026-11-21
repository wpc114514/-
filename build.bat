@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================
echo   划词翻译 - 打包脚本
echo ================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3。
    pause
    exit /b 1
)

if not exist "icon.ico" (
    echo [提示] 未找到图标，正在生成...
    python make_icon.py
)

echo [1/2] 正在打包（约需 1-2 分钟）...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "划词翻译" ^
    --icon "icon.ico" ^
    --add-data "icon.ico;." ^
    main.py

if errorlevel 1 (
    echo.
    echo [失败] 打包出错，请查看上方日志。
    pause
    exit /b 1
)

echo.
echo [2/2] 完成！输出文件：dist\划词翻译.exe
echo.
pause
