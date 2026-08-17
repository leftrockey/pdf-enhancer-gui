# PDF 增强工具 (PDF Enhancer)

针对**扫描版 PDF 文字颜色浅、难以看清**的问题，提供一键增强的离线桌面工具。
通过「灰度渲染 → 对比度拉伸 → gamma 压暗 → 轻度锐化」，让浅灰文字明显变深、背景保持洁白，同时保留灰度层次与插图原貌。

## 功能

- 一键增强整本扫描 PDF（页数与页面尺寸与原件完全一致）
- 极简 GUI：选择文件 → 开始增强 → 进度条 → 输出 `xxx_enhanced.pdf`
- 支持把 PDF 拖拽到程序图标，自动批量处理
- 保留灰度/插图层次，不二值化
- 空白页自动保持原样，不误处理

## 下载

从 [Releases](https://github.com/leftrockey/pdf-enhancer-gui/releases) 下载 `PDF增强工具.exe`。
64 位 Windows 可直接运行，**无需安装 Python，离线可用**。

## 使用

- **双击运行**：界面点「浏览...」选择 PDF → 点「开始增强」，输出到同目录 `xxx_enhanced.pdf`
- **拖拽**：把 PDF 文件拖到 `PDF增强工具.exe` 图标上，自动处理
- **命令行**：`PDF增强工具.exe <文件.pdf> [更多文件.pdf ...]`

默认参数：300 DPI 渲染、gamma 1.5 压暗、JPEG 85 输出。

## 从源码运行 / 打包

```bash
# 依赖
pip install pymupdf numpy scipy pillow

# 直接运行 GUI
python pdf_enhancer_gui.py

# 命令行方式
python enhance_pdf.py --input 测试.pdf --output 测试_enhanced.pdf

# 打包为单文件 exe
build.bat
# 等价命令:
# pyinstaller --onefile --noconsole --name PDF增强工具 --collect-all pymupdf pdf_enhancer_gui.py
```

## 项目结构

| 文件 | 说明 |
|---|---|
| `enhance_pdf.py` | 命令行核心：渲染 + 增强算法 + 并行重建 PDF（空白页守卫） |
| `pdf_enhancer.py` | 线程版批量核心，供 GUI 使用，含进度回调 |
| `pdf_enhancer_gui.py` | tkinter 极简界面 + 拖拽 / 命令行模式 |
| `build.bat` / `PDF增强工具.spec` | PyInstaller 打包脚本 |

## 技术栈

Python 3.12 · PyMuPDF · numpy · scipy · Pillow · tkinter · PyInstaller

## 免责声明

本工具用于增强你自己拥有版权的文档。请勿用于传播受版权保护的图书扫描件。
