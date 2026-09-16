#!/bin/bash
# Build script for macOS: creates a single-file GUI application using PyInstaller
# Usage: chmod +x build_mac.sh && ./build_mac.sh

set -e

# Incremental output directory to avoid overwriting previous builds
D="dist_v2"
for i in {2..99}; do
  if [ ! -d "dist_v$i" ] || [ ! -f "dist_v$i/PDF增强工具" ]; then
    D="dist_v$i"
    break
  fi
done

echo "正在打包, 请稍候(约需数分钟); 输出目录: $D"
pyinstaller --onefile --windowed --name PDF增强工具 --collect-all pymupdf --distpath "$D" pdf_enhancer_gui.py
if [ $? -eq 0 ]; then
  echo
  echo "打包完成: $D/PDF增强工具"
  echo "注意: 生成的是单文件可执行文件，可直接双击运行（前提是已安装所需依赖及tkinter支持）。"
else
  echo
  echo "打包失败, 请查看上方错误信息。"
  exit 1
fi