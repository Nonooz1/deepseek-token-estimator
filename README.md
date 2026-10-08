# DeepSeek Token 用量估算器

把文件 / 压缩包丢进去，先看清楚它要吃掉多少 token，再决定要不要发给 AI。

**为嵌入式工程做了专门优化**：直接指向 Keil 工程打包的 zip，自动认出
`.uvprojx`（MDK v5 / ARM）或 `.uvproj`（uVision 4 / 8051 C51），
跳过编译产物，并支持一键剔掉厂商库（CMSIS / HAL / Driver）。

> **English**: An offline token estimator for the DeepSeek V4 tokenizer.
> Point it at a file, a folder, or a Keil project zip — it extracts the text,
> skips build artifacts, and reports the exact token count. GUI (drag & drop)
> and CLI both included. Docs are in Chinese.

---

## 为什么需要它

上传文件前不算一下，很容易踩两个坑：

**坑一：编译产物比源码还大。** 实测一个 Keil 工程，`.hex` 固件镜像**一个文件**
就占 11,270 token，比全部源码（4,180）还多。而它是编译生成的，对分析代码毫无价值。

**坑二：厂商库吃掉 99% 的窗口。** 实测一个 TI MSPM0 工程（193 个文件）
全量是 **2,369,760 token —— 128K 窗口的 1851%**，根本传不上去。
但其中 99% 是 CMSIS 头文件和 TI 驱动，用户自己的代码只占 0.1%。

这个工具解决的就是这两件事。

---

## 快速开始

### 1. 装环境（只需一次）

```bash
git clone https://github.com/<你的用户名>/deepseek-token-estimator.git
cd deepseek-token-estimator
```

然后 **双击 `setup_env.cmd`**（Windows）。它会自动建好 `.venv` 并装齐依赖。

手动安装也行：

```bash
pip install -r requirements.txt
```

> 唯一硬性要求：Python 3.9+。图形界面还需要 `tkinter`（python.org 的
> Windows 安装包默认自带；如果缺，重跑安装包并勾上 *tcl/tk and IDLE*）。

### 2. 用起来

| 想要 | 怎么做 |
|---|---|
| **图形界面** | 双击 `Token估算器.pyw`，把文件**拖进窗口** |
| **拖到图标上** | 把文件拖到 `drag_files_here.cmd` 上，黑窗出结果 |
| **命令行** | `python estimate.py 工程.zip` |

---

## 图形界面

双击 `Token估算器.pyw`：

- **「文件估算」页** —— 拖文件 / zip / 整个文件夹进来，立刻出结果
- **「粘贴文字」页** —— 粘一段文字，**边打字边实时显示** token 数
- **排除目录**输入框 —— 填目录名（逗号分隔，如 `Driver, CMSIS`），该目录整块不计
- **含编译产物**勾选框 —— 默认不勾；勾上后把 `.o / .axf / .map` 也算进去
- **包内逐个列出**勾选框 —— 默认按扩展名汇总；勾上后列出压缩包里每个文件
- 底部可改「参考上下文窗口」（默认 128000），自动算占比，超了标红

支持 **zip / 7z 压缩包**、Keil 工程、Word、PDF、Excel、各种代码和文本文件。

---

## 命令行

```bash
python estimate.py 工程.zip                     # ★ 最常用：直接算 zip
python estimate.py 工程.zip --all-files         # 列出包内每个文件
python estimate.py 工程.zip --all               # 连编译产物一起算
python estimate.py 工程.zip -q                  # 只要总 token 数

python estimate.py 某个目录                      # 算整个目录
python estimate.py 某个目录 --exclude Driver --exclude CMSIS   # ★ 剔掉厂商库
python estimate.py 某个目录 --window 64000       # 换参考窗口大小

python estimate.py 报告.docx 数据.xlsx 手册.pdf   # 一次算多个
python estimate.py 报告.pdf --detail             # 附上每个文件的开头预览

python count_tokens.py "你好，世界！Hello world!"  # 算一段文字
python count_tokens.py --chat samples/chat.json   # 算对话（含模板开销）
echo "今天天气不错" | python count_tokens.py -     # 管道
```

完整参数：`python estimate.py --help`

---

## 支持的格式

| 类别 | 扩展名 | 默认 |
|---|---|---|
| Keil 工程 | `.uvprojx` `.uvoptx`（v5/ARM）· `.uvproj` `.uvopt`（v4/C51）· `.sct` `.scf` `.icf` `.gpdsc` `.pdsc` | ✅ 计入 |
| 源码 | `.c` `.h` `.cpp` `.hpp` `.s` `.asm` `.a51` `.c51` `.inc` `.ld` `.lds` | ✅ 计入 |
| 文档 | `.docx` `.pdf` `.xlsx` `.md` `.txt` `.json` `.xml` `.csv` | ✅ 计入 |
| 压缩包 | `.zip` `.7z` `.tar` `.tar.gz` `.tgz` `.tar.bz2` `.tar.xz`（可嵌套，默认 3 层） | 展开 |
| **编译产物** | `.o` `.obj` `.axf` `.elf` `.hex` `.bin` `.lib` `.crf` `.d` `.map` `.lst` `.lnp` `.iex` `.sbr` `.__i` `.htm` | ❌ 跳过 |
| **产物目录** | `Objects/` `Listings/` `Output/` `LST/` `DebugConfig/` `si/`（Source Insight）`__pycache__/` `.git/` | ❌ 跳过 |
| **产物文件** | `*.uvguix.<用户名>`（v5）· `*.uvgui.<用户名>`（v4）· `*.build_log.*` · `*.bak` | ❌ 跳过 |
| 二进制 | 按扩展名 + 内容嗅探（含 NUL、控制字符占比 > 30%） | ❌ 跳过 |

加 `--all` 才会把编译产物算进去。

> **目录跳过有保护机制**：万一你自己有个 `Output/` 放源码，里面的 `.c` / `.h`
> 仍会被计入 —— 只有产物扩展名才按目录整块跳过。

### `.rar` 需要外部程序

纯 Python 解不了 rar。装了 **7-Zip** 或 **WinRAR** 后会自动识别；
找不到时会明确提示你先手动解压成 zip。

（Windows 自带的 `tar.exe` 虽然能「列出」rar 成员，但解出来的数据是错的 ——
实测要 5192 字节只给 53 字节 —— 所以没拿它当后端。）

---

## Keil 工程实战

### 例一：MDK v5 / ARM

```
$ python estimate.py STM32F103_Demo.zip

压缩包: STM32F103_Demo.zip
  包内 18 个条目，计入 11 个，跳过编译产物 7 个

  扩展名                文件数        字符数         Token      占比
  ------------------------------------------------------------------
  .c                         3         3,485         1,326     64.0%
  .h                         3           700           248     12.0%
  .uvprojx                   1           567           199      9.6%
  .s                         1           271            95      4.6%
  .sct                       1           171            86      4.2%
```

### 例二：uVision 4 / 8051 C51

```
$ python estimate.py MS51_BMS_C51.zip

压缩包: MS51_BMS_C51.zip
  包内 110 个条目，计入 44 个，跳过编译产物 66 个

  扩展名                文件数        字符数         Token      占比
  ------------------------------------------------------------------
  .h                        21         2,401           764     42.1%
  .c                        18         2,414           723     39.8%
  .uvproj                    1           486           163      9.0%
  .a51                       1           133            58      3.2%
```

110 个条目里只有 44 个是真正要看的，其余 66 个是 `LST/` `Output/` `si/`
里的编译产物和 IDE 缓存。

### 例三：厂商库才是大头（真实工程）

```
$ python estimate.py ~/Documents/empyyyty_project

目录                                            文件数        字符数         Token      占比
--------------------------------------------------------------------------------------------
Driver/ti                                           93     6,127,151     1,666,806     70.3%
Driver/CMSIS                                        27     2,298,728       681,846     28.8%
keil                                                 5        45,749        14,453      0.6%
Core/src                                             3         4,846         1,713      0.1%
Core/inc                                             1         3,343         1,019      0.0%

合计：字符 8,491,285　Token 2,369,760
占参考窗口 128,000 的 1851.4%   ⚠️  超出窗口，需要拆分或精简
```

**237 万 token，是 128K 窗口的 18 倍，根本传不上去。** 但 99% 是厂商库。

剔掉它：

```
$ python estimate.py ~/Documents/empyyyty_project --exclude Driver

合计：字符 65,406　Token 21,108
占参考窗口 128,000 的 16.5%
```

**2,369,760 → 21,108。** 从「装不下」变成「完全放得下」。

- `--exclude` 按**目录名整段匹配**，大小写不敏感，可重复写
- 不会误伤：`--exclude Driver` 不会命中 `mydriver/`
- 文件多时默认**按目录汇总**，加 `--all-files` 才逐个列

---

## ⚠️ 官方脚本有 Bug：中文会被算成 0

原压缩包里的 `deepseek_tokenizer.py` 用的是：

```python
tokenizer = transformers.AutoTokenizer.from_pretrained("./", trust_remote_code=True)
```

在 **transformers 5.x** 下，这行会把 `tokenizer_config.json` 里声明的
`LlamaTokenizerFast` 解析成**慢速的 `LlamaTokenizer`**（SentencePiece 系），
而本包的 `tokenizer.json` 其实是 **BPE** 词表。两者不匹配，后果是：

```text
tokenizer.encode("Hello!")       -> [19923, 3]   ✅ 看着正常
tokenizer.encode("你好，世界")    -> []            ❌ 中文全部被丢掉
```

ASCII 侥幸能过，**所有中日韩文字静默丢失**。装 `sentencepiece` 也修不好。

**正确写法**（跳过 `AutoTokenizer`）：

```python
import transformers
tokenizer = transformers.PreTrainedTokenizerFast.from_pretrained(目录)
tokenizer.encode("你好，世界", add_special_tokens=False)   # -> [30594, 303, 3427]
```

或者用轻量的 `tokenizers`：

```python
from tokenizers import Tokenizer
Tokenizer.from_file("tokenizer.json").encode("你好，世界").ids   # -> [30594, 303, 3427]
```

本仓库所有脚本都已用正确写法。怀疑自己踩坑了就 `python selftest.py`，
第 2 节里 `'你好' -> 1 token` 那行若变成 0 就是踩了。

---

## 自检

任何时候觉得数字可疑，跑一遍：

```bash
python selftest.py
```

覆盖：分词器加载、9 项 token 基线、真实文件抽取、5 种编码识别、二进制过滤、
压缩包与 Keil 工程识别（含 C51 产物命名）、产物过滤边界、`--exclude`、
目录分布、启动脚本完整性、换行符策略、图形界面。

- 命令行环境：**通过 85 项**（无 tkinter 时跳过图形界面那 11 项）
- 图形界面环境：**通过 96 项**

两个环境用不同的分词器后端（`transformers` / `tokenizers`），算出的数字**完全一致**。

> **换行符会影响 token 数**：`samples/sample.txt` 用 LF 是 64 token，
> 转成 CRLF 会变成 73。而 Git for Windows 默认 `core.autocrlf=true`，
> clone 时会偷偷把 LF 转成 CRLF。所以仓库里放了 `.gitattributes`
> （`* -text`）关掉所有转换，保证任何人 clone 到的字节都和提交时一致。
> 如果你要改这个文件，别去掉 `* -text`。

---

## 实测数据（帮你校准直觉）

官方经验值「1 中文字符 ≈ 0.6 token、1 英文字符 ≈ 0.3 token」。
实测（DeepSeek V4，词表 128000）：

| 文本 | 字符数 | 实际 token | 比例 |
|---|---:|---:|---:|
| `你好` | 2 | 1 | 0.50 |
| `你好，世界` | 5 | 3 | 0.60 |
| `今天天气不错` | 6 | 3 | 0.50 |
| `Hello!` | 6 | 2 | 0.33 |
| `！@#$%` | 5 | 4 | 0.80 |
| `こんにちは` | 5 | 5 | 1.00 |
| `한국어` | 3 | 3 | 1.00 |

中文约 **0.5~0.6 token/字**，和官方口径对得上；但标点、日文、韩文明显更贵
（0.8~1.0）。经验比例只能估量级，**要准确数字必须跑分词器**。

真实文件：

| 文件 | 类型 | 字符数 | Token |
|---|---|---:|---:|
| `BMS参数列表.xlsx` | Excel | 9,141 | 5,274 |
| `DW20_920_Communication_Protocol_V1.5(1).pdf` | PDF（7 页） | 7,439 | 2,583 |
| `BMS_Software_Behaviour_Analysis_Report.md` | 文本 | 3,516 | 1,840 |
| 仿真 MDK v5 工程 zip | 压缩包（11 个源文件） | 5,764 | 2,071 |
| 仿真 C51 工程 zip | 压缩包（44 个源文件） | 5,708 | 1,816 |
| TI MSPM0 工程（全量） | 目录（137 个文件） | 8,491,285 | 2,369,760 |
| TI MSPM0 工程（`--exclude Driver`） | 目录（17 个文件） | 65,406 | 21,108 |

### 几个容易忽略的点

- **对话有模板开销**。不是把各条消息的 token 相加，DeepSeek 会插入
  `<｜begin▁of▁sentence｜>`、`<｜User｜>` 等标记。实测样例：正文 14 + 模板 2 = **总 16**。
- **不截断**。配置里 `model_max_length: 16384` 是模型侧限制，本工具给**全文真实 token 数**。
- **PDF 扫描件**没有文字层，提取出来是空的（会标「无可提取文字」），需要先 OCR。
  另外 DeepSeek 网页端上传 PDF 时服务端怎么解析，口径可能和这里不同 ——
  **本工具算的是「提取出来的纯文字」的 token 数**。
- **二进制会被跳过**。按扩展名 + 内容嗅探双重判断。早期版本用 latin-1 兜底，
  而 latin-1 解码**永远不会失败**，结果一个 200KB 随机二进制被算成 **21.8 万 token**。
- **编码自动识别**：`BOM → 无 BOM UTF-16 猜测 → utf-8 → utf-8-sig → gbk → gb18030 → latin-1`。
  Keil 老工程常见的 GBK 中文注释能正确解出。
- **旧版格式不支持**：`.doc` / `.xls` 会提示另存为 `.docx` / `.xlsx`。

---

## 文件清单

| 文件 | 说明 |
|---|---|
| **`Token估算器.pyw`** | ⭐ 双击即用的图形界面 |
| **`estimate.py`** | ⭐ 多格式 + 压缩包估算（图形界面底层也是它） |
| **`count_tokens.py`** | 纯文本 / 对话模板的 token 计算 |
| `setup_env.cmd` | 一键建 `.venv` 并装依赖（Windows） |
| `.gitattributes` | 钉死换行符，防止 clone 后 token 数变化 |
| `start_gui.cmd` / `drag_files_here.cmd` | 备用启动入口 |
| `gui.py` | 图形界面实现 |
| `selftest.py` | 自检脚本 |
| `_make_fixture.py` | 生成两个仿真 Keil 工程（MDK v5 + C51）用于自检 |
| `samples/` | 演示用的 `sample.txt` / `chat.json` |
| `tokenizer.json` / `tokenizer_config.json` | 分词器权重（来自 DeepSeek 官方仓库，未改动） |
| `deepseek_tokenizer.py` | 官方原版脚本（**有中文 Bug，别直接用**，仅作对照保留） |

---

## 依赖

| 包 | 用途 | 必需 |
|---|---|---|
| `tokenizers` | 分词（轻量后端） | ✅ |
| `transformers` + `jinja2` | 分词 + `--chat` 对话模板 | 可选 |
| `pypdf` | PDF | ✅ |
| `python-docx` | Word `.docx` | ✅ |
| `openpyxl` | Excel `.xlsx` | ✅ |
| `py7zr` | `.7z` | ✅ |
| `tkinterdnd2` | 图形界面拖拽 | 可选（缺了只是不能拖） |

`.zip` / `.tar` 用标准库，无需安装。`.rar` 需要系统装 7-Zip 或 WinRAR。

---

## License

[MIT](LICENSE)

`tokenizer.json` / `tokenizer_config.json` 是 DeepSeek 官方模型仓库的分词器定义，
遵循其自身许可，不适用上面的 MIT 条款。
