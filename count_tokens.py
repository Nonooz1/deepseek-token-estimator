#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek V4 Tokenizer 离线用量计算工具
（配套 deepseek_v4_tokenizer.zip，已修正官方脚本在 transformers 5.x 下丢失中文的问题）

用法：
  1) 直接算一段文本
     python count_tokens.py "你好，世界 Hello world!"
  2) 算一个文件
     python count_tokens.py -f article.txt
  3) 从标准输入读（管道）
     echo "你好" | python count_tokens.py -
  4) 算一段对话（含 system/user/assistant 的完整 chat 模板开销）
     python count_tokens.py --chat samples/chat.json
  5) 只看 token 数字（便于脚本调用）
     python count_tokens.py "你好" -q
  6) 打印 token id 序列 + 回译校验
     python count_tokens.py "你好" -t
  7) 不带参数 = 交互模式，逐行输入逐行统计

依赖（二选一）：
  A. 推荐：pip install transformers jinja2      # 支持 --chat 对话模板
  B. 轻量：pip install tokenizers               # 只做纯文本 encode，不支持 --chat
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOKENIZER_JSON = os.path.join(HERE, "tokenizer.json")
TOKENIZER_CONFIG = os.path.join(HERE, "tokenizer_config.json")


def load_tokenizer():
    """返回 (tokenizer, backend_name, supports_chat)"""
    errors = []

    # 路线 A（推荐）：PreTrainedTokenizerFast —— 中文正确 + 带 chat_template
    try:
        import transformers

        tok = transformers.PreTrainedTokenizerFast.from_pretrained(HERE)
        has_tpl = bool(getattr(tok, "chat_template", None))
        return tok, f"transformers {transformers.__version__} (fast)", has_tpl
    except Exception as e:
        errors.append(f"transformers: {e}")

    # 路线 B（轻量）：tokenizers 原生库 —— 纯文本 encode，无 chat 模板
    try:
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(TOKENIZER_JSON)
        return tok, "tokenizers (lightweight)", False
    except Exception as e:
        errors.append(f"tokenizers: {e}")

    sys.stderr.write(
        "无法加载 tokenizer，请先安装依赖：\n"
        "  pip install transformers jinja2\n"
        "或\n"
        "  pip install tokenizers\n\n" + "\n".join(errors) + "\n"
    )
    sys.exit(1)


def encode_ids(tok, text):
    """统一取 token id 列表。注意：不要加 add_special_tokens，
    因为 tokenizer_config.json 里 add_bos_token / add_eos_token 都是 false。"""
    if hasattr(tok, "encode") and hasattr(tok, "convert_ids_to_tokens"):
        return tok.encode(text, add_special_tokens=False)
    return tok.encode(text).ids


def decode_ids(tok, ids):
    if hasattr(tok, "convert_ids_to_tokens"):
        return tok.decode(ids)
    return tok.decode(ids)


def stats(text):
    n_cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    n_ascii = sum(1 for c in text if ord(c) < 128)
    return len(text), n_cjk, n_ascii


def report(tok, backend, text, label="输入", quiet=False, show_tokens=False):
    ids = encode_ids(tok, text)
    n = len(ids)
    n_char, n_cjk, n_ascii = stats(text)

    if quiet:
        print(n)
        return n

    print(f"后端      : {backend}")
    print(f"来源      : {label}")
    print(f"字符数    : {n_char}  (中文 {n_cjk} / ASCII {n_ascii})")
    print(f"Token 数  : {n}")
    if n_char:
        print(f"实际比例  : 1 字符 ≈ {n / n_char:.3f} token")
    if show_tokens:
        print(f"Token IDs : {ids}")
        print(f"回译校验  : {decode_ids(tok, ids)!r}")
    return n


def main():
    ap = argparse.ArgumentParser(description="DeepSeek V4 Tokenizer 离线用量计算")
    ap.add_argument("text", nargs="?", help="要计算的文本；传 - 表示从 stdin 读取")
    ap.add_argument("-f", "--file", help="从文件读取文本")
    ap.add_argument("--chat", help="从 JSON 文件读取消息列表，按官方 chat 模板计算")
    ap.add_argument("-q", "--quiet", action="store_true", help="只输出 token 数字")
    ap.add_argument("-t", "--show-tokens", action="store_true", help="打印 token id 序列")
    args = ap.parse_args()

    tok, backend, supports_chat = load_tokenizer()

    # --- 对话模式 ---
    if args.chat:
        if not supports_chat:
            sys.stderr.write("--chat 需要 transformers 后端，请先 pip install transformers jinja2\n")
            sys.exit(1)
        with open(args.chat, encoding="utf-8") as fh:
            messages = json.load(fh)
        # 用 tokenize=False 拿到渲染后的字符串，再自己 encode。
        # 这样跨 transformers 版本最稳（tokenize=True 返回 BatchEncoding，
        # 不是 dict 子类，且长度是 key 个数而不是 token 个数，容易踩坑）。
        rendered = tok.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        ids = encode_ids(tok, rendered)
        total = len(ids)
        body = sum(len(encode_ids(tok, m.get("content") or "")) for m in messages)
        print(f"后端      : {backend}")
        print(f"消息条数  : {len(messages)}")
        print(f"正文 token: {body}")
        print(f"模板开销  : {total - body}")
        print(f"总 token  : {total}   <- 这才是真正要计费/占上下文的量")
        print()
        print("渲染后的完整 prompt：")
        print(repr(rendered))
        return

    # --- 单段文本 ---
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                text = fh.read()
        except FileNotFoundError:
            sys.stderr.write(f"找不到文件：{args.file}\n")
            sys.exit(2)
        except UnicodeDecodeError as e:
            sys.stderr.write(
                f"文件不是 UTF-8 编码，无法读取：{args.file}\n"
                f"（{e}）\n提示：可先用记事本另存为 UTF-8，或改用 --file 之外的方式。\n"
            )
            sys.exit(2)
        label = args.file
    elif args.text is not None:
        # 注意用 is not None 判断：空字符串 "" 是合法输入（0 token），
        # 不能靠真值判断，否则会误落到交互模式。
        if args.text == "-":
            text, label = sys.stdin.read(), "stdin"
        else:
            text, label = args.text, "命令行参数"
    elif not sys.stdin.isatty():
        text, label = sys.stdin.read(), "stdin"
    else:
        # 交互模式
        print(f"后端: {backend}")
        print("输入文本后回车即可统计（Ctrl+C 退出）：")
        try:
            while True:
                line = input("> ")
                if line:
                    report(tok, backend, line, "交互输入")
                    print()
        except (KeyboardInterrupt, EOFError):
            print()
        return

    report(tok, backend, text, label, quiet=args.quiet, show_tokens=args.show_tokens)


if __name__ == "__main__":
    main()
