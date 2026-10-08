# -*- coding: utf-8 -*-
"""
Token 用量估算器 —— 双击这个文件就能打开图形界面

为什么需要这个文件？
  Windows 把 .pyw 关联到 pyw.exe，双击时用系统 Python 运行、且不弹黑窗。
  但系统 Python 往往没装分词器依赖。所以这里先检查依赖，缺了就自动切换到
  装好依赖的解释器重新启动自己。这样无论双击、还是从任何地方打开，都能跑。

找解释器的顺序：
  1. 当前解释器依赖齐全 → 直接用
  2. 本目录下的虚拟环境（.venv / venv / env）—— 跑过 setup_env.cmd 就会有
  3. PATH 上的 pythonw
  4. 都没有 → 弹窗告诉用户怎么装
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(HERE, "gui.py")

# 必需依赖（tkinterdnd2 是可选的：装不上只是没有拖拽，界面照常）
NEED = ("tokenizers", "pypdf", "docx", "openpyxl")


def missing_deps():
    miss = []
    for m in NEED:
        try:
            __import__(m)
        except Exception:
            miss.append(m)
    return miss


def local_venv_pythonw():
    """本目录下的虚拟环境里的 pythonw.exe（用户跑过 setup_env.cmd 就有）"""
    for name in (".venv", "venv", "env"):
        p = os.path.join(HERE, name, "Scripts", "pythonw.exe")
        if os.path.isfile(p):
            return p
    return None


def same_exe(a, b):
    try:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    except Exception:
        return False


def show_error(msg):
    """没有控制台时用弹窗告知"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("Token 估算器", msg)
        r.destroy()
    except Exception:
        sys.stderr.write(msg + "\n")


def relaunch(exe):
    """换一个解释器把界面拉起来"""
    subprocess.Popen([exe, GUI], cwd=HERE)
    return True


def main():
    # 1) 当前解释器够用，直接跑
    if not missing_deps():
        os.chdir(HERE)
        sys.path.insert(0, HERE)
        import gui
        gui.main()
        return

    # 2) 本目录的虚拟环境
    venv = local_venv_pythonw()
    if venv and not same_exe(venv, sys.executable):
        relaunch(venv)
        return

    # 3) PATH 上的 pythonw
    pw = shutil.which("pythonw")
    if pw and not same_exe(pw, sys.executable):
        relaunch(pw)
        return

    # 4) 实在找不到
    miss = missing_deps()
    show_error(
        "缺少依赖，无法启动：\n\n  " + "\n  ".join(miss) +
        "\n\n当前解释器：\n  " + sys.executable +
        "\n\n最省事的办法：双击本目录下的\n  setup_env.cmd\n"
        "它会自动建好环境并装齐依赖。\n\n"
        "或者手动执行：\n"
        "  pip install -r requirements.txt"
    )


if __name__ == "__main__":
    main()
