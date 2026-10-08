#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 用量估算器 · 图形界面
—— 把文件拖进来，或者粘贴一段文字，立刻看到要花多少 token

配套 estimate.py 使用（复用它的格式解析与分词逻辑）。
"""
import os
import queue
import sys
import threading
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ---- 修正 PROCESSOR_ARCHITECTURE ----
# tkinterdnd2 靠这个环境变量判断该加载哪个 tkdnd 动态库。
# 某些启动方式（被别的程序拉起、精简环境）下它是空的，
# 会导致拖拽初始化失败。这里补一个合理的默认值。
if not os.environ.get("PROCESSOR_ARCHITECTURE"):
    import platform as _plat
    _m = (_plat.machine() or "").strip()
    if _m:
        os.environ["PROCESSOR_ARCHITECTURE"] = _m
    else:
        os.environ["PROCESSOR_ARCHITECTURE"] = "AMD64" if sys.maxsize > 2**32 else "x86"

from estimate import (base_name, count, extract, is_archive,  # noqa: E402
                      iter_entries, load_tokenizer)

# ---- 拖拽支持（tkinterdnd2 装不上也能跑，只是没有拖拽） ----
DND_OK = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_OK = True
except Exception:
    pass

FONT = ("Microsoft YaHei UI", 10)
FONT_SM = ("Microsoft YaHei UI", 9)
FONT_BIG = ("Microsoft YaHei UI", 11, "bold")
MONO = ("Consolas", 10)


def human(n):
    return f"{n:,}" if n >= 1000 else str(n)


class App:
    def __init__(self, root):
        self.root = root
        self.tok = None
        self.backend = ""
        self.q = queue.Queue()
        self.rows = []
        self._text_job = None

        root.title("Token 用量估算器 · DeepSeek V4")
        root.geometry("1000x700")
        root.minsize(820, 560)

        self._build_ui()
        self._start_loader()
        root.after(80, self._poll)

    # ------------------------------------------------------------ 界面搭建
    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            pass

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        self.tab_file = ttk.Frame(nb)
        self.tab_text = ttk.Frame(nb)
        nb.add(self.tab_file, text="  文件估算  ")
        nb.add(self.tab_text, text="  粘贴文字  ")
        self.nb = nb

        self._build_file_tab()
        self._build_text_tab()

        # 底栏
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(bar, text="参考上下文窗口：", font=FONT_SM).pack(side="left")
        self.win_var = tk.StringVar(value="128000")
        ent = ttk.Entry(bar, textvariable=self.win_var, width=9, font=FONT_SM)
        ent.pack(side="left", padx=(0, 4))
        ent.bind("<KeyRelease>", lambda e: self._render_rows())

        ttk.Label(bar, text="token", font=FONT_SM).pack(side="left", padx=(0, 14))
        self.status = ttk.Label(bar, text="正在加载分词器…", font=FONT_SM, foreground="#666")
        self.status.pack(side="left")

    def _build_file_tab(self):
        f = self.tab_file

        self.drop = tk.Label(
            f, text="把文件拖到这里\n\n支持压缩包(zip)、Keil 工程、Word / PDF / Excel、代码文件，可一次拖多个",
            font=FONT, justify="center", bg="#f2f6fc", fg="#31507d",
            bd=2, relief="groove", height=4,
        )
        self.drop.pack(fill="x", padx=10, pady=(10, 6))

        btns = ttk.Frame(f)
        btns.pack(fill="x", padx=10)
        ttk.Button(btns, text="选择文件…", command=self.pick_files).pack(side="left")
        ttk.Button(btns, text="选择文件夹…", command=self.pick_dir).pack(side="left", padx=6)
        ttk.Button(btns, text="清空", command=self.clear_rows).pack(side="left")
        ttk.Button(btns, text="复制结果", command=self.copy_rows).pack(side="left", padx=6)

        self.var_all = tk.BooleanVar(value=False)
        self.var_allfiles = tk.BooleanVar(value=False)
        ttk.Checkbutton(btns, text="含编译产物", variable=self.var_all,
                        command=self._recompute).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(btns, text="包内逐个列出", variable=self.var_allfiles,
                        command=self._recompute).pack(side="left", padx=(6, 0))

        # 排除目录：厂商库（Driver/CMSIS/HAL…）经常是 token 大头，一键剔掉
        exc = ttk.Frame(f)
        exc.pack(fill="x", padx=10, pady=(6, 0))
        ttk.Label(exc, text="排除目录：", font=FONT_SM).pack(side="left")
        self.exc_var = tk.StringVar(value="")
        ent = ttk.Entry(exc, textvariable=self.exc_var, font=FONT_SM)
        ent.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ent.bind("<Return>", lambda e: self._recompute())
        ttk.Button(exc, text="应用", width=6,
                   command=self._recompute).pack(side="left")
        ttk.Label(exc, text="（逗号分隔，如 Driver, CMSIS）",
                  font=FONT_SM, foreground="#888").pack(side="left", padx=(6, 0))
        self.last_paths = []

        cols = ("name", "type", "chars", "tokens", "pct", "note")
        heads = ("文件", "类型", "字符数", "Token", "占比", "备注")
        widths = (250, 70, 90, 90, 70, 260)
        anchors = ("w", "center", "e", "e", "e", "w")

        wrap = ttk.Frame(f)
        wrap.pack(fill="both", expand=True, padx=10, pady=(8, 4))
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=12)
        for c, h, w, a in zip(cols, heads, widths, anchors):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor=a, stretch=(c in ("name", "note")))
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        self.tree.tag_configure("odd", background="#f7f9fc")
        self.tree.tag_configure("bad", foreground="#b3261e")
        self.tree.tag_configure("rollup", background="#eef3fb", font=FONT_SM)

        self.total_lbl = ttk.Label(f, text="", font=FONT_BIG)
        self.total_lbl.pack(anchor="w", padx=10, pady=(2, 10))

        self._setup_dnd()

    def _setup_dnd(self):
        """运行时探测拖拽是否真的可用。
        注意：即使 tkinterdnd2 能 import，如果 root 不是 TkinterDnD.Tk()
        实例，tkdnd 命令并没有加载，注册时会抛 TclError。"""
        ok = False
        if DND_OK and hasattr(self.root, "drop_target_register"):
            try:
                for w in (self.drop, self.tree):
                    w.drop_target_register(DND_FILES)
                    w.dnd_bind("<<Drop>>", self.on_drop)
                ok = True
            except Exception:
                ok = False

        if ok:
            self.drop.configure(
                text="把文件拖到这里\n\n支持 Word / PDF / Excel / txt / md / 代码文件，可一次拖多个")
        else:
            self.drop.configure(
                text="拖拽功能不可用\n\n请点下面的「选择文件…」按钮",
                bg="#fff6e5", fg="#8a5a00")

    def _build_text_tab(self):
        f = self.tab_text
        ttk.Label(f, text="把要发给模型的内容粘到这里，实时看 token 数：", font=FONT_SM).pack(
            anchor="w", padx=10, pady=(10, 4))

        wrap = ttk.Frame(f)
        wrap.pack(fill="both", expand=True, padx=10)
        self.txt = tk.Text(wrap, wrap="word", font=MONO, undo=True)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=vs.set)
        self.txt.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        self.txt.bind("<KeyRelease>", self._on_text_change)

        self.txt_lbl = ttk.Label(f, text="字符 0　·　Token 0", font=FONT_BIG)
        self.txt_lbl.pack(anchor="w", padx=10, pady=8)

    # ------------------------------------------------------------ 分词器加载
    def _start_loader(self):
        def work():
            try:
                tok, backend = load_tokenizer()
                self.q.put(("ready", (tok, backend)))
            except Exception as e:
                self.q.put(("error", e))

        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "ready":
                    self.tok, self.backend = payload
                    self.status.configure(text=f"就绪 · {self.backend}")
                elif kind == "error":
                    self.status.configure(text="分词器加载失败")
                    messagebox.showerror("加载失败", f"无法加载分词器：\n{payload}")
                elif kind == "rows":
                    self.rows = payload
                    self._render_rows()
                elif kind == "busy":
                    self.status.configure(text=payload)
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    # ------------------------------------------------------------ 文件处理
    def on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        self.handle_paths(paths)

    def pick_files(self):
        paths = filedialog.askopenfilenames(
            title="选择要估算的文件",
            filetypes=[
                ("常用文档", "*.docx *.docm *.pdf *.xlsx *.xlsm *.txt *.md *.csv"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self.handle_paths(list(paths))

    def pick_dir(self):
        d = filedialog.askdirectory(title="选择文件夹")
        if d:
            self.handle_paths([d])

    def handle_paths(self, paths):
        if not self.tok:
            messagebox.showinfo("请稍等", "分词器还在加载，稍后再试。")
            return
        self.last_paths = list(paths)
        self._start_work()

    def _recompute(self):
        """勾选框变化时按同样的输入重算一遍"""
        if self.last_paths:
            self._start_work()

    def _start_work(self):
        paths = list(self.last_paths)
        # 必须在主线程读 Tk 变量：tkinter 不是线程安全的，
        # 在子线程里 .get() 会静默失败甚至挂住。
        include_all = bool(self.var_all.get())
        all_files = bool(self.var_allfiles.get())
        exclude = [s.strip().lower() for s in
                   self.exc_var.get().replace("，", ",").split(",") if s.strip()]
        self.status.configure(text=f"正在处理 {len(paths)} 个路径…")
        threading.Thread(target=self._work,
                         args=(paths, include_all, all_files, exclude),
                         daemon=True).start()

    def _archive_rows(self, path, all_files):
        """压缩包：默认按扩展名汇总，all_files=True 时逐个文件列出"""
        import estimate as E
        base = os.path.basename(path)
        try:
            members = list(iter_entries(path))
        except Exception as e:
            return [{"name": base, "type": "压缩包", "chars": None, "tokens": None,
                     "note": f"无法读取: {e}"}]

        included = []
        skipped_art = skipped_bin = 0
        need_tool = None
        for e in members:
            if e.get("reason") == "need_tool":
                need_tool = e.get("note") or "需要外部解压工具"
                continue
            if e["text"] is None:
                if e["type"] == "产物":
                    skipped_art += 1
                else:
                    skipped_bin += 1
                continue
            if not e["text"].strip():
                continue
            included.append({**e, "tok": count(self.tok, e["text"]), "char": len(e["text"])})

        if need_tool:
            return [{"name": base, "type": "压缩包", "chars": None, "tokens": None,
                     "note": f"⚠️ {need_tool}"}]

        bits = [f"包内 {len(members)} 项，计入 {len(included)}"]
        if skipped_art:
            bits.append(f"跳过产物 {skipped_art}")
        if skipped_bin:
            bits.append(f"跳过二进制 {skipped_bin}")
        info = "；".join(bits)

        out = []
        if all_files:
            for e in included:
                out.append({"name": f"{base} › {e['name']}", "type": e["type"],
                            "chars": e["char"], "tokens": e["tok"], "note": ""})
        else:
            groups = {}
            for e in included:
                ext = os.path.splitext(E.base_name(e["name"]))[1].lower() or "(无扩展名)"
                g = groups.setdefault(ext, {"files": 0, "char": 0, "tok": 0})
                g["files"] += 1
                g["char"] += e["char"]
                g["tok"] += e["tok"]
            for ext, g in sorted(groups.items(), key=lambda kv: -kv[1]["tok"]):
                out.append({"name": f"{base} › {ext}", "type": "压缩包",
                            "chars": g["char"], "tokens": g["tok"],
                            "note": f"{g['files']} 个文件"})

        out.append({"name": f"{base}（合计）", "type": "压缩包",
                    "chars": sum(e["char"] for e in included),
                    "tokens": sum(e["tok"] for e in included),
                    "note": info, "rollup": True})
        return out

    def _work(self, paths, include_all=False, all_files=False, exclude=None):
        import estimate as E
        E.INCLUDE_ARTIFACTS = include_all
        E.EXCLUDE_PATS = list(exclude or [])

        targets = []
        for p in paths:
            if os.path.isdir(p):
                for root, _, names in os.walk(p):
                    for n in sorted(names):
                        targets.append((os.path.join(root, n), False))
            elif os.path.isfile(p):
                targets.append((p, True))

        rows = []
        for path, explicit in targets:
            name = os.path.basename(path)

            if is_archive(path):
                rows.extend(self._archive_rows(path, all_files))
                continue

            if E.in_excluded(path):
                rows.append({"name": name, "type": "排除", "chars": None,
                             "tokens": None, "note": "跳过（已排除的目录）"})
                continue

            if not E.INCLUDE_ARTIFACTS and not explicit and \
                    (E.in_skip_dir(path) or E.is_artifact(path)):
                rows.append({"name": name, "type": "产物", "chars": None,
                             "tokens": None, "note": "跳过（编译产物）"})
                continue

            try:
                text, label, note = extract(path)
            except Exception as e:
                rows.append({"name": name, "type": "?", "chars": None,
                             "tokens": None, "note": f"读取异常: {e}"})
                continue
            if text is None:
                rows.append({"name": name, "type": label, "chars": None,
                             "tokens": None, "note": note})
                continue
            try:
                n = count(self.tok, text)
            except Exception as e:
                rows.append({"name": name, "type": label, "chars": None,
                             "tokens": None, "note": f"分词失败: {e}"})
                continue
            rows.append({"name": name, "type": label, "chars": len(text),
                         "tokens": n, "note": note})

        rows.sort(key=lambda r: (r["tokens"] is None, -(r["tokens"] or 0)))
        self.q.put(("rows", rows))

    def clear_rows(self):
        self.rows = []
        self.last_paths = []
        self._render_rows()

    def copy_rows(self):
        if not self.rows:
            return
        lines = ["文件\t类型\t字符数\tToken\t备注"]
        for r in self.rows:
            lines.append("{}\t{}\t{}\t{}\t{}".format(
                r["name"], r["type"],
                human(r["chars"]) if r["chars"] is not None else "-",
                human(r["tokens"]) if r["tokens"] is not None else "-",
                r["note"]))
        total = sum(r["tokens"] for r in self.rows if r["tokens"])
        lines.append(f"合计\t\t\t{human(total)}")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.status.configure(text="结果已复制到剪贴板")

    # ------------------------------------------------------------ 渲染
    def _window(self):
        try:
            w = int(self.win_var.get().replace(",", "").strip())
            return w if w > 0 else 128000
        except Exception:
            return 128000

    def _render_rows(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        win = self._window()
        total_tok = 0
        total_char = 0

        for idx, r in enumerate(self.rows):
            tags = ["odd"] if idx % 2 else []
            pct = ""
            if r["tokens"] is not None:
                # rollup 行是压缩包的小计，只展示，不计入总计，否则会翻倍
                if not r.get("rollup"):
                    total_tok += r["tokens"]
                    total_char += r["chars"] or 0
                p = r["tokens"] / win * 100
                pct = f"{p:.1f}%"
                if p > 100:
                    tags.append("bad")
            if r.get("rollup"):
                tags.append("rollup")
            self.tree.insert(
                "", "end",
                values=(r["name"], r["type"],
                        human(r["chars"]) if r["chars"] is not None else "-",
                        human(r["tokens"]) if r["tokens"] is not None else "-",
                        pct, r["note"]),
                tags=tuple(tags),
            )

        if not self.rows:
            self.total_lbl.configure(text="")
            return

        p = total_tok / win * 100
        warn = ""
        if p > 100:
            warn = "　⚠️ 超出窗口，需要拆分或精简"
        elif p > 60:
            warn = "　⚠️ 占用偏高，会挤压对话空间"
        self.total_lbl.configure(
            text=f"合计 {len(self.rows)} 个文件　字符 {human(total_char)}　"
                 f"Token {human(total_tok)}　（占 {human(win)} 的 {p:.1f}%）{warn}"
        )

    # ------------------------------------------------------------ 文本实时统计
    def _on_text_change(self, _event=None):
        if self._text_job:
            self.root.after_cancel(self._text_job)
        self._text_job = self.root.after(180, self._count_text)

    def _count_text(self):
        self._text_job = None
        s = self.txt.get("1.0", "end-1c")
        if not self.tok:
            self.txt_lbl.configure(text="分词器加载中…")
            return
        n = count(self.tok, s) if s else 0
        win = self._window()
        p = n / win * 100
        self.txt_lbl.configure(
            text=f"字符 {human(len(s))}　·　Token {human(n)}　（占 {human(win)} 的 {p:.1f}%）"
        )


def main():
    try:
        if DND_OK:
            root = TkinterDnD.Tk()
        else:
            root = tk.Tk()
        App(root)
        root.mainloop()
    except Exception:
        # 用 pythonw 启动时没有控制台，出错必须留痕 + 弹窗
        tb = traceback.format_exc()
        log = os.path.join(HERE, "error.log")
        try:
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(tb + "\n")
        except Exception:
            pass
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror(
                "启动失败",
                f"Token 估算器启动失败：\n\n{tb[-1200:]}\n\n详细信息已写入：\n{log}")
            r.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
