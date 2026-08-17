@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在打包, 请稍候(约需数分钟)...
pyinstaller --onefile --noconsole --name PDF增强工具 --collect-all pymupdf pdf_enhancer_gui.py
if %errorlevel%==0 (
  echo.
  echo 打包完成: dist\PDF增强工具.exe
) else (
  echo.
  echo 打包失败, 请查看上方错误信息。
)
