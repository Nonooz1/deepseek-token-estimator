# DeepSeek Token 用量估算器

> 把文件丢给 AI 之前，先算清楚它要吃掉多少 token。

**离线 · 精确 · 拖拽即用。**

跑的是 **DeepSeek V4 官方分词器**（词表 128000），不是按字符数估的。
适用于 **DeepSeek API** 调用、**Codex**、以及各类 AI Agent 的上下文管理。

> **English**: An offline token estimator for the DeepSeek V4 tokenizer.
> Point it at a file, a folder, or a Keil project zip — it extracts the text,
> skips build artifacts, and reports the exact token count. Drag-and-drop GUI
> included. Docs are in Chinese.

---

## 应用场景

**1. 控制 DeepSeek API 成本与上下文占用**
发之前就知道这次要花多少 token，超出窗口提前发现，不用等接口报错。

**2. Codex / Agent 工作流**
把文件或整个目录交给 Agent 前先过一遍，别让无关内容挤占上下文。

**3. 嵌入式工程（Keil）**
直接指向工程打包的 zip，自动认出 **MDK v5（ARM）** 与 **uVision 4（8051 C51）**
工程文件，跳过 `.o / .hex / .map` 等编译产物。

实测一个工程里**单个 `.hex` 固件镜像就有 11,270 token，比全部源码还多**。
还能一键剔除厂商库（CMSIS / HAL / Driver）—— 实测某 TI MSPM0 工程
全量 **237 万 token**（128K 窗口的 18 倍），剔除厂商库后降到 **2.1 万**，立刻可用。

---

## 图形界面（推荐用法）

**双击 `Token估算器.pyw`**，把文件拖进窗口就行。

- **拖拽**：文件、文件夹、zip 一起拖进来，立刻出结果
- **粘贴文字**：边打字边实时显示 token 数
- **排除目录**：填 `Driver, CMSIS` 就能整块剔掉厂商库
- **参考窗口**：可改（默认 128000），自动算占比，超了标红
- **含编译产物**：默认不勾；需要时勾上把 `.o / .hex / .map` 也算进来

---

## 安装

需要 Python 3.9+。

```bash
git clone https://github.com/Nonooz1/deepseek-token-estimator.git
cd deepseek-token-estimator
```

**双击 `setup_env.cmd`** 即可 —— 自动建好 `.venv` 并装齐依赖。

手动装也行：`pip install -r requirements.txt`

---

## 命令行（可选）

```bash
python estimate.py 工程.zip
python estimate.py 某个目录 --exclude Driver --exclude CMSIS
python estimate.py 工程.zip --all-files        # 逐个文件列出
python count_tokens.py "一段文字"               # 纯文本计数
python count_tokens.py --chat samples/chat.json # 对话（含模板开销）
```

完整参数：`python estimate.py --help`

---

## 支持的文件

| 类别 | 内容 |
|---|---|
| 压缩包 | `.zip` `.7z` `.tar*`（可嵌套展开）；`.rar` 需系统装 7-Zip / WinRAR |
| 文档 | `.docx` `.pdf` `.xlsx` `.md` `.txt` `.csv` `.json` `.xml` |
| 代码 | `.c` `.h` `.cpp` `.hpp` `.s` `.asm` `.a51` `.inc` `.ld` |
| 工程 | `.uvprojx` `.uvproj` `.uvopt` `.uvoptx` `.sct` `.icf` |
| 自动跳过 | 编译产物、二进制文件、IDE 缓存目录（加 `--all` 可强制计入） |

编码自动识别（UTF-8 / GBK / UTF-16），Keil 老工程的中文注释也能正确读出。

---

## 为什么数字可信

⚠️ DeepSeek 官方示例脚本里的 `AutoTokenizer` 在 **transformers 5.x** 下会
**静默丢弃全部中文** —— `encode("你好，世界")` 返回 `[]`，而英文看着一切正常。

本项目已改用 `PreTrainedTokenizerFast`，中日韩文字正常计数。

---

## License

[MIT](LICENSE)

`tokenizer.json` / `tokenizer_config.json` 是 DeepSeek 官方模型仓库的分词器定义，
遵循其自身许可，不适用上面的 MIT 条款。
