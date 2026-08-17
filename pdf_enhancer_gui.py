# -*- coding: utf-8 -*-
"""PDF 增强工具 —— 极简离线 GUI。

双击运行打开窗口: 选 PDF -> 开始增强 -> 生成 <原名>_enhanced.pdf。
附带 CLI 模式: 直接传入文件路径(或把 PDF 拖到 exe 上)即可批量增强。

打包: pyinstaller --onefile --noconsole --name PDF增强工具 --collect-all pymupdf pdf_enhancer_gui.py
"""

import os
import queue
import sys
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pdf_enhancer import enhance_pdf


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.busy = False

        root.title("PDF 增强工具")
        root.resizable(False, False)

        frm = ttk.Frame(root, padding=14)
        frm.grid(sticky="nsew")

        # 输入行
        ttk.Label(frm, text="PDF 文件:").grid(row=0, column=0, sticky="w", pady=4)
        self.input_var = tk.StringVar()
        ent = ttk.Entry(frm, textvariable=self.input_var, width=40)
        ent.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        self.browse_btn = ttk.Button(frm, text="浏览...", command=self.browse)
        self.browse_btn.grid(row=0, column=2, pady=4)

        # 输出行
        ttk.Label(frm, text="输出:").grid(row=1, column=0, sticky="w", pady=4)
        self.output_var = tk.StringVar()
        ttk.Label(frm, textvariable=self.output_var, foreground="#666").grid(
            row=1, column=1, columnspan=2, sticky="w", pady=4)

        # 开始按钮
        self.start_btn = ttk.Button(frm, text="开始增强", command=self.start)
        self.start_btn.grid(row=2, column=0, columnspan=3, pady=(10, 8), sticky="ew")

        # 进度条 + 状态
        self.bar = ttk.Progressbar(frm, mode="determinate", maximum=100)
        self.bar.grid(row=3, column=0, columnspan=3, sticky="ew", pady=4)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(frm, textvariable=self.status_var, foreground="#444").grid(
            row=4, column=0, columnspan=3, sticky="w")

        frm.columnconfigure(1, weight=1)
        self.root.after(100, self._poll)

    def browse(self):
        path = filedialog.askopenfilename(
            title="选择要增强的 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")])
        if path:
            self.input_var.set(path)
            self._set_output(path)

    def _set_output(self, in_path):
        base, _ = os.path.splitext(in_path)
        self.output_var.set(base + "_enhanced.pdf")

    def start(self):
        if self.busy:
            return
        in_path = self.input_var.get().strip().strip('"')
        if not in_path:
            messagebox.showwarning("提示", "请先选择 PDF 文件")
            return
        if not os.path.isfile(in_path):
            messagebox.showerror("错误", f"文件不存在:\n{in_path}")
            return
        if not self.output_var.get().strip():
            self._set_output(in_path)
        out_path = self.output_var.get().strip().strip('"')
        if os.path.exists(out_path):
            if not messagebox.askyesno("覆盖确认", f"输出文件已存在, 是否覆盖?\n{out_path}"):
                return

        self.busy = True
        self.browse_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.bar["value"] = 0
        self.status_var.set("正在打开...")

        threading.Thread(target=self._job, args=(in_path, out_path), daemon=True).start()

    def _job(self, in_path, out_path):
        try:
            stats = enhance_pdf(in_path, out_path, progress_cb=self._on_progress)
            self.q.put(("done", out_path, stats))
        except Exception as e:  # noqa: BLE001 - 任何异常都应告知用户
            self.q.put(("error", str(e)))

    def _on_progress(self, done, total):
        self.q.put(("progress", done, total))

    def _poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, done, total = msg
                    self.bar["maximum"] = total
                    self.bar["value"] = done
                    self.status_var.set(f"正在处理 {done}/{total} 页...")
                elif kind == "done":
                    _, out_path, stats = msg
                    self.bar["value"] = self.bar["maximum"]
                    self.status_var.set(
                        f"完成: {stats['pages']} 页, 暗像素占比 "
                        f"{stats['orig_dark_mean']*100:.1f}% -> {stats['new_dark_mean']*100:.1f}%")
                    self._reset_buttons()
                    messagebox.showinfo("完成", f"增强完成!\n\n输出文件:\n{out_path}")
                elif kind == "error":
                    _, err = msg
                    self.status_var.set("失败")
                    self._reset_buttons()
                    messagebox.showerror("出错", f"处理失败:\n{err}")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _reset_buttons(self):
        self.browse_btn.config(state="normal")
        self.start_btn.config(state="normal")
        self.busy = False


def cli_mode(args):
    """无 GUI 直接增强传入的文件(支持多个), 用于无头自测 / 拖拽到 exe 批量处理。"""
    files = [a for a in args if a.lower().endswith(".pdf") and os.path.isfile(a)]
    if not files:
        print("用法: PDF增强工具 <文件.pdf> [更多.pdf ...]")
        return 1
    ok = True
    for f in files:
        base, _ = os.path.splitext(f)
        out = base + "_enhanced.pdf"
        try:
            stats = enhance_pdf(f, out)
            print(f"{f} -> {out} | pages={stats['pages']} "
                  f"dark {stats['orig_dark_mean']*100:.2f}% -> {stats['new_dark_mean']*100:.2f}%")
        except Exception as e:  # noqa: BLE001
            print(f"失败: {f}: {e}")
            ok = False
    return 0 if ok else 1


def main():
    if len(sys.argv) > 1:
        sys.exit(cli_mode(sys.argv[1:]))
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
