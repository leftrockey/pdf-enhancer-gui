# -*- coding: utf-8 -*-
"""PDF 增强核心模块(线程版批量入口)。

复用 enhance_pdf.py 中已验证的算法(enhance_gray / _process_page),
提供适合 GUI/打包的线程池批量入口 + 进度回调。
"""

from concurrent.futures import ThreadPoolExecutor

import fitz  # PyMuPDF
import numpy as np

from enhance_pdf import enhance_gray, _process_page

# 默认参数(已验证: 300 DPI, gamma 1.5, JPEG 85)
DEFAULT_DPI = 300
DEFAULT_GAMMA = 1.5
DEFAULT_JPEG_QUALITY = 85
DEFAULT_WORKERS = 4


def enhance_pdf(input_path, output_path, dpi=DEFAULT_DPI, gamma=DEFAULT_GAMMA,
                jpeg_quality=DEFAULT_JPEG_QUALITY, workers=DEFAULT_WORKERS,
                progress_cb=None) -> dict:
    """对整本 PDF 逐页增强并重建输出, 保持页数/页面尺寸与原件一致。

    progress_cb(done: int, total: int) 每完成一页回调一次(在调用线程内, 非 worker)。
    返回 {"pages", "orig_dark_mean", "new_dark_mean"}。
    """
    src = fitz.open(input_path)
    page_rects = [src[i].rect for i in range(src.page_count)]
    total = src.page_count
    src.close()
    if total == 0:
        raise ValueError("输入 PDF 无页面")

    out = fitz.open()
    orig_darks, new_darks = [], []

    jobs = ((input_path, i, dpi, gamma, jpeg_quality) for i in range(total))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (img, od, nd) in enumerate(ex.map(_process_page, jobs, chunksize=1)):
            page = out.new_page(width=page_rects[i].width, height=page_rects[i].height)
            page.insert_image(page.rect, stream=img)
            orig_darks.append(od)
            new_darks.append(nd)
            if progress_cb:
                progress_cb(i + 1, total)

    out.save(output_path, garbage=4, deflate=True)
    out.close()

    return {
        "pages": total,
        "orig_dark_mean": float(np.mean(orig_darks)) if orig_darks else 0.0,
        "new_dark_mean": float(np.mean(new_darks)) if new_darks else 0.0,
    }
