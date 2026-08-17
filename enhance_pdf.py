# -*- coding: utf-8 -*-
"""扫描版 PDF 文字浅/发灰 的自然灰度增强工具。

流程: 灰度渲染 -> 背景归一 -> 分位数对比度拉伸 -> gamma 暗化 -> 轻度锐化 -> 重建 PDF。
保留灰度层次与插图原貌, 不二值化, 不加 OCR 文字层。

用法:
    python enhance_pdf.py --input 测试.pdf --output 测试_enhanced.pdf
    python enhance_pdf.py --input 书.pdf --output 书_enhanced.pdf --dpi 300 --gamma 0.8
"""

import argparse
import os
from concurrent.futures import ProcessPoolExecutor

import fitz  # PyMuPDF
import numpy as np
from scipy import ndimage


# ============ 可调参数 ============
DEFAULT_DPI = 200          # 渲染分辨率 (px/inch), 越高字越细, 文件越大
GAMMA = 1.5                # >1 压暗中间调(文字笔画), 背景仍近白; 越大字越黑
P_LO, P_HI = 1.0, 99.5     # 对比度拉伸的分位数区间 (%)
BG_NORM = False            # 是否做背景归一化(消除扫描阴影/反光不匀); 干净扫描可关
BG_SIGMA = 60.0            # 背景估计高斯核 sigma (px @ DPI), 需远大于笔画宽度
SHARPEN_AMOUNT = 0.3       # unsharp 锐化强度, 0 表示关闭
SHARPEN_SIGMA = 1.0        # unsharp 高斯核 sigma (px)
# ==================================


def enhance_gray(gray: np.ndarray, gamma: float = GAMMA) -> np.ndarray:
    """对单页灰度图做自然增强, 返回 uint8 灰度图。

    gray: float64, [0,255], 背景亮、文字浅灰。
    gamma: >1 压暗中间调(浅灰文字笔画); 由参数显式传入(跨进程安全, 不依赖全局)。
    """
    g = gray.astype(np.float64)

    if BG_NORM:
        bg = ndimage.gaussian_filter(g, sigma=BG_SIGMA, mode="nearest")
        bg = np.maximum(bg, 1.0)
        g = g / bg * 255.0

    # 分位数对比度拉伸
    lo, hi = np.percentile(g, [P_LO, P_HI])
    if hi - lo < 1.0:           # 整页近乎一色(空白页/全黑页): 不做拉伸, 保持原样
        return np.clip(g, 0, 255).astype(np.uint8)
    g = (g - lo) / (hi - lo) * 255.0
    g = np.clip(g, 0, 255)

    # gamma 压暗中间调(文字笔画)
    g = 255.0 * np.power(g / 255.0, gamma)

    # 轻度 unsharp 锐化
    blur = ndimage.gaussian_filter(g, sigma=SHARPEN_SIGMA, mode="nearest")
    g = g + SHARPEN_AMOUNT * (g - blur)

    return np.clip(g, 0, 255).astype(np.uint8)


def _render_page(filepath: str, index: int, dpi: int) -> np.ndarray:
    """渲染指定页为灰度图 (numpy float64 [0,255])。"""
    doc = fitz.open(filepath)
    try:
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = doc[index].get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    finally:
        doc.close()
    gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    return gray.astype(np.float64)


def _dark_ratio(g: np.ndarray) -> float:
    return float((g < 128).mean())


def _process_page(args):
    """子进程单页处理: 渲染 -> 增强 -> 编码图像流。返回 (img_bytes, 原暗比, 新暗比)。

    jpeg_quality>0 时输出 JPEG(体积小), 否则输出 PNG(无损)。
    """
    filepath, index, dpi, gamma, jpeg_quality = args
    g = _render_page(filepath, index, dpi)
    orig_dark = _dark_ratio(g)
    out = enhance_gray(g, gamma=gamma)
    new_dark = _dark_ratio(out)
    h, w = out.shape
    pix = fitz.Pixmap(fitz.csGRAY, w, h, out.tobytes(), False)
    if jpeg_quality > 0:
        return pix.tobytes("jpeg", jpg_quality=jpeg_quality), orig_dark, new_dark
    return pix.tobytes("png"), orig_dark, new_dark


def build_enhanced_pdf(input_path: str, output_path: str, dpi: int, gamma: float, workers: int, jpeg_quality: int = 0) -> dict:
    """并行增强全部页面并重建 PDF, 保持页数/页面尺寸与原件一致。"""
    src = fitz.open(input_path)
    page_rects = [src[i].rect for i in range(src.page_count)]
    total = src.page_count
    src.close()
    if total == 0:
        raise ValueError("输入 PDF 无页面")

    out = fitz.open()
    orig_darks, new_darks = [], []

    with ProcessPoolExecutor(max_workers=workers) as ex:
        jobs = ((input_path, i, dpi, gamma, jpeg_quality) for i in range(total))
        for i, (img, od, nd) in enumerate(ex.map(_process_page, jobs, chunksize=1)):
            page = out.new_page(width=page_rects[i].width, height=page_rects[i].height)
            page.insert_image(page.rect, stream=img)
            orig_darks.append(od)
            new_darks.append(nd)
            print(f"page {i+1}/{total}: orig_dark={od:.4f} -> new_dark={nd:.4f}", flush=True)

    out.save(output_path, garbage=4, deflate=True)
    out.close()

    return {
        "pages": total,
        "orig_dark_mean": float(np.mean(orig_darks)),
        "new_dark_mean": float(np.mean(new_darks)),
    }


def main():
    ap = argparse.ArgumentParser(description="扫描版 PDF 文字浅灰的自然灰度增强")
    ap.add_argument("--input", "-i", default=r"测试.pdf")
    ap.add_argument("--output", "-o", default=r"测试_enhanced.pdf")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument("--gamma", type=float, default=GAMMA)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--jpeg-quality", type=int, default=90,
                    help="输出图像 JPEG 质量(1-100); 0 表示用 PNG 无损")
    args = ap.parse_args()

    print(f"input={args.input}  output={args.output}  dpi={args.dpi}  gamma={args.gamma}  workers={args.workers}  jpeg={args.jpeg_quality}")
    stats = build_enhanced_pdf(args.input, args.output, args.dpi, args.gamma, args.workers, args.jpeg_quality)

    print("\n===== 汇总 =====")
    print(f"pages         : {stats['pages']}")
    print(f"暗像素占比(均值) : 原图 {stats['orig_dark_mean']:.4f}  ->  增强 {stats['new_dark_mean']:.4f}")
    print(f"输出文件       : {os.path.abspath(args.output)} ({os.path.getsize(args.output)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
