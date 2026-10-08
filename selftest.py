# -*- coding: utf-8 -*-
"""
自检脚本 —— 确认这套工具没坏

用法：
  python selftest.py

会依次检查：
  1. 分词器能否加载，且中文没有被吞掉（这是最关键的一项）
  2. 一批已知输入的 token 数是否与基线一致
  3. 各种格式的文件抽取是否正常
  4. 图形界面能否正常构造（需要 tkinter，缺了就跳过）
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PASS, FAIL = [], []


def check(name, got, want):
    if got == want:
        PASS.append(name)
        print(f"  [OK]   {name}")
    else:
        FAIL.append(name)
        print(f"  [FAIL] {name}  期望 {want!r}，实际 {got!r}")


print("=" * 62)
print("1. 分词器加载")
print("=" * 62)

try:
    from estimate import count, extract, load_tokenizer
    tok, backend = load_tokenizer()
    print(f"  后端: {backend}")
    PASS.append("加载分词器")
except Exception as e:
    print(f"  [FAIL] 加载失败: {e}")
    sys.exit(1)

# ---- 最关键：中文不能被吞 ----
print()
print("=" * 62)
print("2. Token 计数基线（中文非 0 是关键）")
print("=" * 62)

BASE = [
    ("", 0),
    ("你好", 1),
    ("你好，世界", 3),
    ("今天天气不错", 3),
    ("Hello!", 2),
    ("DeepSeek 分词", 5),
    ("！@#$%", 4),
    ("こんにちは", 5),
    ("한국어", 3),
]
for text, want in BASE:
    check(f"{text!r} -> {want} token", count(tok, text), want)

# 明确点出这个经典故障
if count(tok, "你好") == 0:
    print()
    print("  !! 中文被算成 0 token —— 你八成用了 AutoTokenizer，")
    print("     请改用 PreTrainedTokenizerFast.from_pretrained(目录)。")

# ---- 文件抽取 ----
print()
print("=" * 62)
print("3. 文件格式抽取")
print("=" * 62)

# 样例目录：仓库自带的在 samples/；本机另有一批真实文件在 Downloads/。
# 两个地方都找，找不到就跳过 —— 保证这份自检在别人机器上也能跑。
SAMPLE_DIRS = [os.path.join(HERE, "samples"), os.path.expanduser("~/Downloads")]


def find_sample(name):
    for d in SAMPLE_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


sample_txt = find_sample("sample.txt")
if sample_txt:
    text, label, note = extract(sample_txt)
    check("sample.txt 可读取", text is not None, True)
    check("sample.txt token 数", count(tok, text), 64)

# 挑几个真实文件试试（存在才测）
cands = [
    ("BMS参数列表.xlsx", "Excel", 5274),
    ("BMS_Software_Behaviour_Analysis_Report.md", "文本", 1840),
    ("DW20_920_Communication_Protocol_V1.5(1).pdf", "PDF", 2583),
]
for fname, want_label, want_tok in cands:
    path = find_sample(fname)
    if not path:
        print(f"  [skip] {fname} 不存在")
        continue
    try:
        text, label, note = extract(path)
    except Exception as e:
        check(f"{fname} 抽取", f"异常 {e}", "正常")
        continue
    check(f"{fname} 类型", label, want_label)
    check(f"{fname} token", count(tok, text), want_tok)

# ---- 编码与二进制识别 ----
print()
print("=" * 62)
print("3b. 编码识别 / 二进制过滤（临时文件，测完即删）")
print("=" * 62)

import shutil          # noqa: E402
import tempfile        # noqa: E402

tmp = tempfile.mkdtemp(prefix="tokselftest_")
try:
    cases = [
        # (文件名, 字节内容, 期望备注, 期望正文)
        # 注意：纯 utf-8 是默认情况，extract() 故意不给备注，避免表格噪音
        ("utf8.txt", "你好，世界 UTF-8".encode("utf-8"), "", "你好，世界 UTF-8"),
        ("utf8bom.txt", "你好，世界 UTF-8".encode("utf-8-sig"), "编码 utf-8-sig", "你好，世界 UTF-8"),
        ("gbk.txt", "你好，世界 GBK".encode("gbk"), "编码 gbk", "你好，世界 GBK"),
        ("utf16.txt", "你好，世界 UTF16".encode("utf-16"), "编码 utf-16", "你好，世界 UTF16"),
        ("utf16le.txt", "Hello ASCII UTF16".encode("utf-16-le"), "编码 utf-16-le", "Hello ASCII UTF16"),
    ]
    for fname, data, want_note, want_text in cases:
        p = os.path.join(tmp, fname)
        with open(p, "wb") as fh:
            fh.write(data)
        text, label, note = extract(p)
        check(f"{fname} 解码正确", text, want_text)
        check(f"{fname} 备注", note, want_note)
        check(f"{fname} token 数", count(tok, text), count(tok, want_text))

    # 二进制必须被拦下，不能被 latin-1 兜底读成几十万 token
    import random
    random.seed(42)
    p = os.path.join(tmp, "random.txt")      # 故意用 .txt 伪装
    with open(p, "wb") as fh:
        fh.write(bytes(random.randrange(256) for _ in range(20000)))
    text, label, note = extract(p)
    check("随机二进制被识别", text is None, True)
    check("随机二进制类型标签", label, "二进制")

    p = os.path.join(tmp, "empty.txt")
    open(p, "wb").close()
    text, label, note = extract(p)
    check("空文件可读取", text, "")
    check("空文件 token 数", count(tok, text), 0)

    p = os.path.join(tmp, "legacy.doc")
    with open(p, "wb") as fh:
        fh.write(b"\xd0\xcf\x11\xe0")
    text, label, note = extract(p)
    check("旧版 .doc 被拦下", text is None, True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---- 压缩包 / Keil 工程 ----
print()
print("=" * 62)
print("3c. 压缩包与 Keil 工程识别（临时 zip，测完即删）")
print("=" * 62)

import zipfile as _zipfile    # noqa: E402

tmp2 = tempfile.mkdtemp(prefix="tokzip_")
try:
    import estimate as E

    inner = io.BytesIO()
    with _zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("nested/deep.c", "int deep(void) { return 42; }\n")

    zpath = os.path.join(tmp2, "Proj.zip")
    with _zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("Proj/MDK-ARM/Proj.uvprojx", "<Project><Device>STM32F103</Device></Project>")
        zf.writestr("Proj/Core/Src/main.c", "int main(void) { return 0; }\n")
        zf.writestr("Proj/Core/Inc/main.h", "#ifndef MAIN_H\n#define MAIN_H\n#endif\n")
        zf.writestr("Proj/MDK-ARM/startup.s", "  .syntax unified\n  .thumb\n")
        # 产物目录 + 产物扩展名：默认都要跳过
        zf.writestr("Proj/MDK-ARM/Objects/main.o", b"\x7fELF" + bytes(range(256)) * 4)
        zf.writestr("Proj/MDK-ARM/Listings/Proj.map", "Symbol  Address  Size\n" * 200)
        zf.writestr("Proj/MDK-ARM/Proj.uvguix.hp", "<Layout><Height>800</Height></Layout>")
        # 嵌套压缩包
        zf.writestr("Proj/vendor.zip", inner.getvalue())

    check("识别为压缩包", E.is_archive(zpath), True)

    # 默认：跳过产物
    E.INCLUDE_ARTIFACTS = False
    entries = list(E.iter_entries(zpath))
    included = [e for e in entries if e["text"] is not None and e["text"].strip()]
    names = {E.base_name(e["name"]) for e in included}

    check("包内条目总数", len(entries), 8)
    check("默认计入的文件数", len(included), 5)          # uvprojx/c/h/s + 嵌套里的 deep.c
    check("跳过产物目录 (.o)", "main.o" in names, False)
    check("跳过产物扩展名 (.map)", "Proj.map" in names, False)
    check("跳过 uvguix 布局文件", "Proj.uvguix.hp" in names, False)
    check("Keil 工程文件被识别", "Proj.uvprojx" in names, True)
    check("汇编文件被识别", "startup.s" in names, True)
    check("嵌套压缩包被展开", "deep.c" in names, True)

    total = sum(count(tok, e["text"]) for e in included)
    check("包内合计 token 与逐条求和一致", total,
          count(tok, "int main(void) { return 0; }\n")
          + count(tok, "#ifndef MAIN_H\n#define MAIN_H\n#endif\n")
          + count(tok, "<Project><Device>STM32F103</Device></Project>")
          + count(tok, "  .syntax unified\n  .thumb\n")
          + count(tok, "int deep(void) { return 42; }\n"))

    # --all：产物也要算进来（.map 是文本，应被计入；.o 仍是二进制）
    E.INCLUDE_ARTIFACTS = True
    entries_all = list(E.iter_entries(zpath))
    included_all = [e for e in entries_all if e["text"] is not None and e["text"].strip()]
    check("--all 后计入数变多", len(included_all) > len(included), True)
    check("--all 后 .map 被计入", "Proj.map" in {E.base_name(e["name"]) for e in included_all}, True)
    check("--all 后 .o 仍是二进制", "main.o" in {E.base_name(e["name"]) for e in included_all}, False)
    E.INCLUDE_ARTIFACTS = False

    # extract() 对压缩包应返回全部文本拼接，token 数与逐条求和一致
    ztext, zlabel, _ = extract(zpath)
    check("extract(压缩包) 类型标签", zlabel, "压缩包")
    check("extract(压缩包) token 总数", count(tok, ztext), total)

    # 不存在的压缩包要友好报错，不能抛异常
    bad = os.path.join(tmp2, "broken.zip")
    with open(bad, "wb") as fh:
        fh.write(b"this is not a zip file at all")
    e0 = list(E.iter_entries(bad))
    check("损坏的 zip 被友好处理", len(e0) == 1 and e0[0]["text"] is None, True)
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# ---- 产物过滤的边界 / --exclude / 目录分布 ----
print()
print("=" * 62)
print("3d. 产物过滤边界、--exclude、目录分布（纯内存，无临时文件）")
print("=" * 62)

import estimate as E2    # noqa: E402

# 目录撞名保护：产物目录里若真有源码，不能被整目录丢掉
GUARD = [
    ("P/Output/main.c", False),        # 撞名目录里的真源码 -> 保留
    ("P/Output/app.h", False),
    ("P/Output/x.obj", True),          # 撞名目录里的产物 -> 跳过
    ("P/Output/x.hex", True),
    ("P/si/code.c", False),            # si/ 里的源码 -> 保留
    ("P/si/idx.IAB", True),            # Source Insight 索引 -> 跳过
    ("P/LST/a.lst", True),
    ("P/Objects/a.crf", True),
    ("P/Core/main.c", False),          # 正常目录
    ("P/UserProj.uvgui.admin", True),  # uVision 4 的 .uvgui.<用户名>
    ("P/UserProj.uvguix.hp", True),    # uVision 5 的 .uvguix.<用户名>
    ("P/UserProj.uvproj", False),      # 工程文件保留
    ("P/Output/TZ3.lnp", True),        # C51 链接中间文件
    ("P/Output/Common.__i", True),
    ("P/Output/X.SBR", True),
    ("P/Startup/STARTUP.A51", False),  # C51 启动汇编要保留
]
for p, want_skip in GUARD:
    got = E2.in_skip_dir(p) or E2.is_artifact(p)
    check(f"{'跳过' if want_skip else '计入'} {p}", got, want_skip)

# --exclude：按目录名整段匹配
E2.EXCLUDE_PATS = ["driver", "cmsis"]
check("--exclude 命中 Driver/", E2.in_excluded("P/Driver/ti/x.h"), True)
check("--exclude 命中 Driver/CMSIS/", E2.in_excluded("P/Driver/CMSIS/y.h"), True)
check("--exclude 不误伤 Core/", E2.in_excluded("P/Core/main.c"), False)
check("--exclude 不误伤 mydriver/", E2.in_excluded("P/mydriver/z.c"), False)
E2.EXCLUDE_PATS = []

# 目录分布汇总
detail = [
    (os.path.join("R", "Core", "main.c"), 100, 40),
    (os.path.join("R", "Core", "app.c"), 200, 60),
    (os.path.join("R", "Driver", "a.h"), 900, 300),
]
rows = E2._dir_rollup(detail)
as_dict = {r[0]: r[3] for r in rows}
check("目录分布按 token 降序", rows[0][0], "Driver")
check("目录分布 Core 合计", as_dict.get("Core"), 100)
check("目录分布 Driver 合计", as_dict.get("Driver"), 300)

# ---- 启动脚本完整性 ----
print()
print("=" * 62)
print("3e. 启动脚本完整性（.cmd 必须纯 ASCII + CRLF）")
print("=" * 62)

CRLF = bytes([13, 10])
LF = bytes([10])
for fn in ("setup_env.cmd", "start_gui.cmd", "drag_files_here.cmd"):
    p = os.path.join(HERE, fn)
    if not os.path.exists(p):
        check(f"{fn} 存在", False, True)
        continue
    raw = open(p, "rb").read()
    check(f"{fn} 是纯 ASCII", [b for b in raw if b > 127], [])
    check(f"{fn} 无裸 LF", raw.replace(CRLF, b"").count(LF), 0)

# 启动器里不该再出现写死的个人路径
launcher = os.path.join(HERE, "Token估算器.pyw")
if os.path.exists(launcher):
    src = open(launcher, encoding="utf-8").read()
    check("启动器不含写死的个人路径", "C:\\Users\\" in src, False)

# ---- 图形界面 ----
print()
print("=" * 62)
print("4. 图形界面")
print("=" * 62)

try:
    import tkinter  # noqa
    has_tk = True
except Exception:
    has_tk = False

if not has_tk:
    print("  [skip] 当前解释器没有 tkinter，跳过图形界面自检")
    print(f"         （图形界面请用：{os.path.join(HERE, 'Token估算器.pyw')}）")
else:
    try:
        import tkinter as tk

        if not os.environ.get("PROCESSOR_ARCHITECTURE"):
            import platform
            os.environ["PROCESSOR_ARCHITECTURE"] = platform.machine() or "AMD64"

        import gui

        root = gui.TkinterDnD.Tk() if gui.DND_OK else tk.Tk()
        root.withdraw()
        app = gui.App(root)

        import time
        deadline = time.time() + 60
        while app.tok is None and time.time() < deadline:
            root.update()
            time.sleep(0.05)

        check("图形界面分词器就绪", app.tok is not None, True)
        check("图形界面中文计数", gui.count(app.tok, "你好，世界"), 3)
        check("拖拽支持已启用", gui.DND_OK, True)

        app.txt.insert("1.0", "人工智能正在改变世界。" * 10)
        app._count_text()
        check("文本页实时统计", "Token 50" in app.txt_lbl.cget("text"), True)

        # 压缩包在图形界面里的处理
        zpath = os.path.join(HERE, "_fixture", "STM32F103_Demo.zip")
        if not os.path.exists(zpath):
            print("  [skip] 没有 _fixture/STM32F103_Demo.zip，跳过压缩包界面测试")
            print("         （可运行 _make_fixture.py 生成）")
        else:
            app.rows = []
            app.handle_paths([zpath])
            deadline = time.time() + 90
            while not app.rows and time.time() < deadline:
                root.update()
                time.sleep(0.05)

            check("界面处理压缩包产生结果行", len(app.rows) > 0, True)
            rollups = [r for r in app.rows if r.get("rollup")]
            check("界面有压缩包小计行", len(rollups), 1)
            detail = sum(r["tokens"] for r in app.rows
                         if r["tokens"] and not r.get("rollup"))
            check("小计行等于各分组之和（未翻倍）",
                  rollups[0]["tokens"] if rollups else None, detail)

            # 勾选"包内逐个列出"后应重算成逐文件视图
            app.var_allfiles.set(True)
            app.rows = []
            app._recompute()
            deadline = time.time() + 90
            while not app.rows and time.time() < deadline:
                root.update()
                time.sleep(0.05)
            check("勾选逐个列出后行数变多", len(app.rows) > len(rollups), True)

        # 排除目录：界面上的输入框要真的生效
        import tempfile as _tf
        tdir = _tf.mkdtemp(prefix="tokgui_")
        try:
            os.makedirs(os.path.join(tdir, "Core"))
            os.makedirs(os.path.join(tdir, "Driver"))
            with open(os.path.join(tdir, "Core", "main.c"), "w", encoding="utf-8") as fh:
                fh.write("int main(void) { return 0; }\n")
            with open(os.path.join(tdir, "Driver", "big.h"), "w", encoding="utf-8") as fh:
                fh.write("#define X 1\n" * 300)

            app.var_allfiles.set(False)
            app.exc_var.set("")
            app.rows = []
            app.handle_paths([tdir])
            deadline = time.time() + 60
            while not app.rows and time.time() < deadline:
                root.update()
                time.sleep(0.05)
            check("未排除时 Driver 被计入",
                  any(r["name"] == "big.h" and r["tokens"] for r in app.rows), True)

            app.exc_var.set("Driver")
            app.rows = []
            app._recompute()
            deadline = time.time() + 60
            while not app.rows and time.time() < deadline:
                root.update()
                time.sleep(0.05)
            check("排除 Driver 后 big.h 不计入",
                  any(r["name"] == "big.h" and r["tokens"] for r in app.rows), False)
            check("排除 Driver 后 main.c 仍在",
                  any(r["name"] == "main.c" and r["tokens"] for r in app.rows), True)
        finally:
            shutil.rmtree(tdir, ignore_errors=True)

        root.destroy()
    except Exception as e:
        import traceback
        print(f"  [FAIL] 图形界面自检异常: {e}")
        traceback.print_exc()
        FAIL.append("图形界面")

# ---- 汇总 ----
print()
print("=" * 62)
print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)
print("=" * 62)
sys.exit(1 if FAIL else 0)
