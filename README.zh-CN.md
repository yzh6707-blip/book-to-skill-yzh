<p align="center">
  <a href="README.md">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <img src="docs/assets/logo.png" alt="book-to-skill logo" width="120">
</p>

<h1 align="center">book-to-skill</h1>

<p align="center">
  <strong>把任何技术书籍、文档文件夹或资料合集，变成一个统一的 Agent 技能——在 GitHub Copilot CLI、Amp、Claude Code、Trae 或 CodeBuddy 中边工作边研读、查阅和应用。</strong>
</p>

<p align="center">
  <a href="https://github.com/yzh6707-blip/book-to-skill-yzh/releases"><img src="https://img.shields.io/github/v/release/yzh6707-blip/book-to-skill-yzh?style=for-the-badge&color=blueviolet" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Agent_Skills-Open_Standard-blueviolet?style=for-the-badge" alt="Agent Skills standard">
  <img src="https://img.shields.io/badge/PDF%20%E2%80%A2%20EPUB%20%E2%80%A2%20DOCX%20%E2%80%A2%20MD%20%E2%80%A2%20HTML%20%E2%80%A2%20RTF%20%E2%80%A2%20MOBI-%E6%94%AF%E6%8C%81-green?style=for-the-badge" alt="Formats supported">
  <img src="https://img.shields.io/badge/Security-bidi%20%7C%20XXE%20%7C%20%E6%B3%A8%E5%85%A5%E9%98%B2%E6%8A%A4-blue?style=for-the-badge" alt="Security hardened">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License">
</p>

<p align="center">
  <a href="#-为什么">为什么</a> ·
  <a href="#-新增内容">新增内容</a> ·
  <a href="#-它会生成什么">它会生成什么</a> ·
  <a href="#-使用方法">使用方法</a> ·
  <a href="#-依赖要求">依赖要求</a> ·
  <a href="#-工作原理">工作原理</a> ·
  <a href="#-安全">安全</a> ·
  <a href="#-常见问题">常见问题</a> ·
  <a href="#-安装">安装</a> ·
  <a href="#-独立-cli">CLI</a> ·
  <a href="docs/ARCHITECTURE.md">架构</a>
</p>

<p align="center">
  <strong>比把整本书塞进上下文少用 24×–51× 的 token</strong>（真实书籍实测，<a href="docs/PERFORMANCE.md">测量方法</a>）。
</p>

**三步工作原理：**

1. **指向**文件、文件夹或通配符 —— `/book-to-skill ./我的书.pdf`
2. **它提炼**成技能 —— 框架、决策规则、反模式、分章文件。要的是结构，不是摘要。
3. **你的 Agent 按需加载** —— 问 `/我的书 复制` 时它读取对应章节，从真实内容作答，不编造。

---

## 🤔 为什么

你买了一本好书。读完一遍。三个月后，你连第 7 章的存在都忘了。

常见的替代方案都不好用：
- 📄「让我直接搜 PDF」→ 得到的是一串页码，不是答案
- 🧠「我让 Agent 聊聊这本书」→ 它要么编造，要么说没有内容
- 📝「我边读边做笔记」→ 最后得到一份再也不打开的 200 行文档

**book-to-skill 的解法：把书变成一个结构化的技能，让 Agent 按需加载。**

装好之后，你只要输入 `/你的书名 复制`，Agent 就会读取对应章节，从真实内容作答。不编造、不翻 PDF，书真正进入你的工作流。

兼容任何支持开放 [Agent Skills](https://github.com/agentskills/agentskills) 标准的主机——GitHub Copilot CLI、Amp、Claude Code、Trae、CodeBuddy 和 WorkBuddy 读取的都是同一种 `SKILL.md` 格式。

---

## ✨ 新增内容

本 fork 对原版转换器做了加固和扩展。原版功能全部保留，以下是新增项：

**正确性与安全**
- **bidi 提示注入防护** —— 抽取和生成技能扫描现在会清除 bidi 覆盖/隔离控制符（U+202A–U+202E、U+2066–U+2069）以及零宽字符，堵住真实存在的文档注入攻击向量。
- **修复 EPUB 阅读顺序** —— `ebooklib` 遍历的是清单而非 spine，出版方若在清单中乱序排列章节，会得到乱序文本（而 stdlib 回退路径反而是对的）。现在两条路径共用同一个 OPF spine 解析器。
- **保留 DOCX 表格位置** —— `python-docx` 路径不再把表格全部排到段落之后；两条抽取路径都按文档顺序输出。
- **`pdfminer` 增加 120 秒超时** —— 损坏的 PDF 不再让 CLI 永久卡死。
- **修复 PDF 连字符** —— `well-\nknown` 这类折行复合词保持为 `well-known`，不再被错误合并成 `wellknown`。

**生成产物校验（不再是不负责任的承诺）**
- **`tools/validate_generated.py`** —— 结构门禁：检查 frontmatter、章节索引链接是否真实存在、必备章节标题、token 预算，以及**加粗术语在原书文本中的可溯源校验（grounding）**。错误为硬失败；与安全扫描一起在工作流第 9.5 步执行。

**效率与体验**
- **内容哈希抽取缓存** —— 未变更的源文件不再重复解析（对 PDF/docling/OCR 和增量更新流程收益巨大）；`--no-cache` 强制全量重抽。
- **`probe` 子命令** —— 跨平台（Windows/PowerShell 友好）的 `wc`/`grep`/`sed` 替代：行数/字数/token 统计、带行号的章节边界、`--chapter N` 章节文本切片。
- **CJK 感知的 token 估算** —— 中/日/韩文本按字符数估算（约 1.5 字符/token），不再用英文词数启发式（此前会低估 3–4 倍）。
- **非交互模式** —— `BOOK_SKILL_ASSUME` / `BOOK_SKILL_ASSUME_DEPTH` / `BOOK_SKILL_NO_PROMPT` 让 CI 和脚本化流水线全程免提示运行。
- **并发安全** —— PID 锁 + 残留文件清理，防止并行运行互相覆盖共享工作目录。
- **OCR 开关** —— 按每页平均字符数判断扫描版，支持 `BOOK_SKILL_FORCE_OCR` / `BOOK_SKILL_NO_OCR` / `BOOK_SKILL_OCR_THRESHOLD` 覆盖。

---

## 📦 它会生成什么

运行 `/book-to-skill 你的书.pdf`（或文件夹、通配符、文件列表）会在 Agent 的技能目录中生成完整技能（Copilot CLI 为 `~/.copilot/skills/<slug>/`，Amp 或跨 Agent 为 `~/.agents/skills/<slug>/`，Claude Code 为 `~/.claude/skills/<slug>/`，CodeBuddy 为 `~/.codebuddy/skills/<slug>/`，WorkBuddy 为 `~/.workbuddy/skills/<slug>/`）：

| 文件 | 用途 | 大小 |
|------|------|------|
| `SKILL.md` | 核心心智模型 + 章节索引 | ~4,000 tokens |
| `chapters/ch01-*.md` … | 每章一个文件，按需加载 | ~1,000 tokens/章 |
| `glossary.md` | 所有关键术语，字母排序 + 章节引用 | ~1,500 tokens |
| `patterns.md` | 所有技巧、算法和设计模式 | ~2,000 tokens |
| `cheatsheet.md` | 决策表和速查规则 | ~1,000 tokens |

**章节文件按需加载** —— 在你问到对应主题之前，不计入技能预算。

---

## 🚀 使用方法

```
/book-to-skill <文档文件夹或通配符路径>... [技能名称-slug]
```

支持格式：PDF、EPUB、DOCX、TXT、Markdown、reStructuredText、AsciiDoc、HTML、RTF、MOBI/AZW/AZW3。

**示例：**

```bash
# 多个文件合并为一个技能
/book-to-skill ~/论文/论文1.pdf ~/笔记/导出.txt 研究合集

# 处理文件夹中所有支持的文件
/book-to-skill ~/工作区/项目文档/ 项目知识库

# 处理匹配通配符的文件
/book-to-skill "~/书籍/*.epub" 我的书库

# 把新资料增量合并进已有技能
/book-to-skill ~/文章/新论文.pdf ~/.claude/skills/项目知识库
```

**非交互 / CI 运行** —— 用环境变量代替问答：

```bash
BOOK_SKILL_ASSUME=technical BOOK_SKILL_ASSUME_DEPTH=study BOOK_SKILL_NO_PROMPT=1 \
  /book-to-skill ./我的书.pdf
```

生成之后，像使用任何 Agent 技能一样使用它：

```bash
/数据密集型应用系统设计                    # 加载核心心智模型
/数据密集型应用系统设计 复制                # 查找并讲解某个主题
/数据密集型应用系统设计 ch05               # 深入第 5 章
/数据密集型应用系统设计 "你有哪些章节？"
```

GitHub Copilot CLI 可能需要先运行 `/skills reload`，新技能才会出现在 `/skills list`。Claude Code、Amp、Trae、CodeBuddy 和 WorkBuddy 在下一个会话自动加载。

---

## 🔧 依赖要求

抽取器按格式逐个尝试工具、用第一个可用的。全部未装时会告诉你该运行哪条命令。纯文本、Markdown、reStructuredText 和 AsciiDoc 无需额外依赖。

> **一条命令检查环境：** `python3 -m book_to_skill --check` 会打印每种格式安装了哪些抽取器，以及缺失时该装什么——无需准备任何文件。

**PDF —— 按书型选择：**

| 书型 | 工具 | 安装 | 速度 |
|------|------|------|------|
| 文字为主（散文、表格少） | `pdftotext`（poppler） | `sudo apt install poppler-utils` | ⚡ 瞬时 |
| 文字为主（备选） | `pypdf` | `pip3 install pypdf` | ⚡ 瞬时 |
| 文字为主（备选） | `pdfminer.six` | `pip3 install pdfminer.six` | ⚡ 瞬时 |
| **技术书（代码、表格、公式）** | **`docling`** | `pip3 install docling` | ~1.5 秒/页 |
| **扫描版（无文字层）** | `tesseract` + `pdftoppm` | `sudo apt install tesseract-ocr poppler-utils` | 慢，自动 |

> 抽取前会先问这本书是**技术书**还是**文字为主**，自动选择合适工具。Docling 保留 Markdown 表格和代码块；pdftotext 对纯文字书更快。文字层过薄（每页平均少于约 30 字符）的 PDF 会被当作扫描版自动尝试 OCR——用 `BOOK_SKILL_NO_OCR=1` 关闭、`BOOK_SKILL_FORCE_OCR=1` 强制。

**EPUB：**

| 工具 | 安装 | 质量 |
|------|------|------|
| `ebooklib` + `beautifulsoup4` | `pip3 install ebooklib beautifulsoup4` | ⭐⭐⭐ 最佳 |
| 标准库 `zipfile` | 内置，无需安装 | ⭐⭐ 始终可用 |

**其他格式：**

| 格式 | 工具 | 安装 |
|------|------|------|
| DOCX | `python-docx`（回退：标准库 ZIP/XML） | `pip3 install python-docx` |
| HTML | `beautifulsoup4`（回退：标准库 `html.parser`） | `pip3 install beautifulsoup4` |
| RTF | `striprtf`（回退：正则） | `pip3 install striprtf` |
| MOBI / AZW / AZW3 | Calibre `ebook-convert`（外部程序） | https://calibre-ebook.com/download |
| TXT / Markdown / reStructuredText / AsciiDoc | 内置 | — |

---

## ⚙️ 工作原理

```
一个文件 · 一个文件夹 · 一个通配符 · 一串路径
     │
     ▼
第 1.5 步 — "技术书还是文字为主？"   （CI 可用 BOOK_SKILL_ASSUME=… 跳过）
     │
     ├── technical → Docling  （表格 + 代码块转 Markdown，~1.5 秒/页）
     └── text      → pdftotext → pypdf → pdfminer  （瞬时）
     │
     ▼
book_to_skill <路径…> --mode <technical|text>
  每个源文件：PDF → pdftotext/Docling/OCR · EPUB → ebooklib → stdlib zipfile
               （单个坏文件跳过并告警，其余照常处理）
  内容哈希缓存：未变更的源文件直接复用，不重新解析
     │
     ├── <工作目录>/full_text.txt   （所有源文件合并，带来源标记）
     └── <工作目录>/metadata.json   （汇总统计 + 每个源文件的明细，含 sha256）
               │
               ▼
          Agent 分析结构
          （书名、作者、章节、目录——跨所有来源）
          ── 或针对已有技能：把新内容增量合并（模式 4）
               │
               ▼
          逐章生成摘要  （每章 800–1,200 tokens）
          technical 类型 → 额外生成 Code Examples + Reference Tables 章节
          生成术语表、模式库、速查表
          生成主 SKILL.md（核心心智模型）
               │
               ▼
第 9.5 步 — 校验门禁（两个都必须通过）：
  1. validate_generated.py  → frontmatter、章节链接、标题、预算、grounding 溯源
  2. scan_generated_skill.py → 提示注入 / 权威性扫描
               │
               ▼
          技能写入以下之一：
            ~/.copilot/skills/<slug>/     ~/.agents/skills/<slug>/
            ~/.claude/skills/<slug>/       ~/.codebuddy/skills/<slug>/
            ~/.workbuddy/skills/<slug>/
          <工作目录>/                       🗑️ 清理（cache/ 保留）
```

**抽取基准**（103 页技术书，纯 CPU）：

| 方法 | 耗时 | Tokens | 表格 | 代码块 |
|------|------|--------|------|--------|
| pdftotext | 0.1s | 27K | 0 | 0 |
| Docling | 164s | 27K（+1.2%） | 48 | 36 |

**真实转换**（实测：页数、抽取 tokens、自动检测章节数、Claude Sonnet 4.5 按 \$3/\$15 每百万 token 估算单次成本）：

| 书名 | 格式 | 页数 | Tokens | 章节 | ~成本 |
|------|------|-----:|-------:|-----:|------:|
| Think Python 2 | PDF | 244 | 119K | 19 | \$0.88 |
| Working Backwards | PDF | 371 | 175K | 10 | \$0.96 |
| Pro Git | PDF | 501 | 229K | — † | \$1.23 |
| Moby-Dick | EPUB | — | 301K | — † | \$1.42 |

† 章节自动检测需要明确的 `Chapter N` / `Capítulo N` 标题。Pro Git 用小节标题、Moby-Dick 用章名/罗马数字，所以两者都未自动分段——抽取和转换仍然可用，只是需要手动指定小节。一本完整技能的成本大约 **每本 \$1**；远比每次会话重读 PDF 便宜。

<details>
<summary>设计原则（点击展开）</summary>

1. **密度优先于完整** —— 1,000 token 的摘要胜过 10,000 token 的摘录
2. **实践者口吻** ——「当 Y 时用 X」，而不是「本书阐述了 X」
3. **SKILL.md 前置** —— 压缩保证前 ~5,000 token 是最重要的内容，先写最有用的
4. **章节按需加载** —— 主题索引告诉 Claude 该读哪个文件；章节只在需要时加载
5. **绝不照搬原文** —— 始终综合、总结、提取信号
6. **输出可溯源** —— 加粗的框架名必须能在源文本中找到；`validate_generated.py` 强制校验

</details>

---

## 🛡️ 安全

文档携带的提示注入被严肃对待。流水线分三层防御：

1. **抽取层**（`book_to_skill/sanitize.py`）—— 清除用于走私指令的不可见码点：零宽字符、Unicode 标签块，以及 bidi 覆盖/隔离控制符（U+202A–U+202E、U+2066–U+2069）——这些字符可以在 diff 中完全不可见地反转文本的显示顺序。
2. **生成规范**（`SKILL.md`）—— 指示 Agent 把源文本当作数据、绝不当作指令，并对可疑指令保持警惕。
3. **生成后扫描**（`tools/scan_generated_skill.py`）—— 审计成品技能中残留的不可见字符与权威/注入模式；与 `tools/validate_generated.py` 一起作为第 9.5 步的硬门禁运行。

其他加固：DOCX/EPUB 抽取做了 XML 实体安全（无 XXE）、子进程调用从不使用 shell、单源失败被隔离（坏文件跳过，批次继续）。

---

## ❓ 常见问题

**「我直接把 PDF/EPUB 丢进 Claude 项目上下文不行吗？」**

可以——但每次对话都会预先烧掉那份 token 预算。400 页的书约 200K tokens。用技能的话，只有与问题相关的章节会加载——通常是 SKILL.md 核心（~4K）加上你问到的那一章（~1K）。其余内容留在磁盘上，直到你需要它。

经济学是**摊销**而非大小。粘贴整本书，是**每次会话的每一轮、永远**支付全额 token 账单。book-to-skill 的抽取成本**只付一次**，以后每次对话只加载需要的切片。

更重要的是：原始文本注入是检索，技能是推理。加载章节文件时，Claude 不是在搜索关键词匹配——它在处理预先提取的、命名清晰的框架、原则和心智模型，这些内容是为**应用**而结构化整理的，不是为阅读准备的。

---

**「Claude 现在有 1M token 上下文了，直接把整本书一直加载着不行吗？」**

更大的窗口改变的是「装得下什么」，不是「什么更聪明」：

- **按 token、按调用付费。** 技能加载的是 KB，不是 MB。
- **内容越多，回忆越差。** 回答一个问题，1K 的精选章节胜过 200K 的原始散文。
- **窗口 ≠ 结构。** 技能自带预提取的框架——是推理，不是检索。

大窗口适合对再也不会用到的材料做一次性处理。技能适合你会反复使用的知识。

---

**「这不就是 RAG 吗？」**

RAG 在查询时工作：切块 → 向量化 → 找相似 → 塞进提示。book-to-skill 在**编译时**工作：一次深度分析提取作者真正的框架、命名、说明何时使用、捕捉反模式。

- **宽而浅** —— 几十本书的库，「找到提到 X 的部分」→ RAG 工具更合适。
- **窄而深** —— 一本书或一组紧密相关的资料，工作时应用其框架 → book-to-skill 更合适。

两者互补：RAG 给书架做索引，book-to-skill 精读一本书。

---

**「热门书 Claude 训练数据里已经有了，何必麻烦？」**

对广为人知的书，Claude 有泛化知识——但它是压缩的、被全网讨论平均过的，而且可能对具体引文或章节位置产生幻觉。book-to-skill 基于**你实际拥有的副本**工作，而且生成的技能**经过 grounding 校验**：每个加粗框架名都必须在你的源文本中逐字出现，所以输出不可能凭空发明框架。

它更擅长 Claude 完全不知道的书：冷门技术参考、公司内部文档、新近出版物、译著。

---

## 📥 安装

> **两种用法，请勿混淆：**
> - **作为 Agent 技能**（Claude Code、Copilot CLI、Amp、Trae、CodeBuddy 或 WorkBuddy 中的 `/book-to-skill` 命令）→ **`git clone` 到你的技能文件夹**（见下）。这给你斜杠命令和完整的转书流程。
> - **作为独立 CLI**（仅文本抽取器）→ `pip install book-to-skill`，然后 `book-to-skill --help`。这**不会**注册 Agent 技能，只安装抽取引擎。见[独立 CLI 章节](#-独立-cli)。

本技能遵循开放 [Agent Skills](https://github.com/agentskills/agentskills) 标准，一次安装即可用于任何兼容主机。

**GitHub Copilot CLI**（个人技能）：

```bash
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.copilot/skills/book-to-skill
# 然后在 copilot 会话中：
/skills reload
/skills info book-to-skill
```

或 Copilot CLI 与 Amp 都能发现的跨 Agent 路径：

```bash
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.agents/skills/book-to-skill
```

**Claude Code：**

```bash
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.claude/skills/book-to-skill
```

**Trae / CodeBuddy / WorkBuddy** —— 同一标准，不同目录：

```bash
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.trae/skills/book-to-skill    # 或工作区的 .trae/skills/
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.codebuddy/skills/book-to-skill
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.workbuddy/skills/book-to-skill
```

然后在任意 Agent 会话中：

```bash
/book-to-skill ~/path/to/your-book.pdf
# 或
/book-to-skill ~/path/to/your-book.epub
```

---

## 🧰 独立 CLI（pip）

`pip install book-to-skill` 是**独立、可选**的路径。它只安装文本抽取引擎 CLI，用于脚本化或获取可选抽取器；**不会**注册 `/book-to-skill` Agent 技能（要技能请用上面的 `git clone`）。

```bash
pip install "book-to-skill[pdf,epub,docx]"   # 引擎 + 可选抽取器
book-to-skill ~/path/to/book.pdf --mode text  # 或：python -m book_to_skill ...
book-to-skill --check                          # 报告安装了哪些抽取器
book-to-skill probe book.pdf                   # 行数 + 带行号的章节地图
book-to-skill probe book.pdf --chapter 3       # 只输出第 3 章文本（Windows 安全的 sed）
book-to-skill book.pdf --no-cache              # 强制重新抽取（默认有内容哈希缓存）
```

抽取**按内容 SHA-256 缓存**（`<工作目录>/cache/`）：未变更的源文件直接跳过解析——对增量更新流程和慢速 PDF/docling/OCR 抽取尤其有用。`--no-cache` 强制全量重抽。并行运行受工作目录锁保护。

---

## 📁 仓库结构

```
book-to-skill/
├── SKILL.md                 # 技能定义 + 分步说明（生成器规范）
├── book_to_skill/           # 模块化抽取包
│   ├── cli.py               # 控制台入口
│   ├── config.py            # 扩展名、路径、依赖常量
│   ├── dependencies.py      # 可选依赖探测 + --check
│   ├── exceptions.py        # ExtractionError（单源失败，批次安全）
│   ├── sanitize.py          # 零宽 / 标签块 / bidi 提示注入清洗
│   ├── utils.py             # CLI 解析、多源解析、章节检测、
│   │                        # 内容哈希缓存、工作目录锁、probe 子命令
│   └── parsers/             # pdf、epub、docx、html、rtf、calibre、text
├── tools/
│   ├── discovery_tax.py         # 度量 token 成本 vs 上下文转储 / discovery loop
│   ├── validate_skill.py        # 对照主机规则检查生成的 SKILL.md（--lens …）
│   ├── validate_generated.py    # 结构门禁：链接、标题、预算、grounding 溯源
│   └── scan_generated_skill.py  # 对生成技能做提示注入扫描
├── tests/                   # pytest 套件（抽取、检测、缓存、probe、安全）
├── docs/
│   ├── PERFORMANCE.md       # 实测基准、discovery tax、成本
│   └── ARCHITECTURE.md      # 流水线 + 组件图
├── CHANGELOG.md             # 发布历史（semver）
├── CONTRIBUTING.md          # 开发环境、PR 规范、发布流程
├── SECURITY.md              # 漏洞报告
├── README.md                # 本文件（英文）
└── README.zh-CN.md          # 本文件（简体中文）
```

---

## ⚖️ 版权与合理使用

book-to-skill **不附带任何书籍内容**——一页都没有。它是一个转换器，指向你已经拥有的文件。

- **处理在本地完成。** 抽取和分析在你的机器上运行。本工具不上传你的文件。（如果你的 Agent 模型运行在云端，你喂给它的文本遵循该提供商通常的数据条款——与任何提示词一样。）
- **使用你自己的副本。** 带上一本你买的书、公司拥有的文档，或你有权阅读的论文。
- **输出是你的笔记。** 生成的技能是结构化、综合后的衍生品——框架名、定义、要点——不是原文的复制。技能明确从不照抄原文段落（见质量规则 #7）。把它当作手写学习笔记：属于你，仅供个人使用。
- **不要分发。** 发布或分享受版权作品的生成技能可能侵权。第三方书籍的技能请保持私有。内部文档、你自己的写作和开放许可的材料，在各自许可范围内可以分享。

拿不准时，遵循源文档的许可或条款。本项目只是一个工具；如何使用取决于你。

---

## License / 许可证

MIT —— 适用于本仓库中的转换器（代码 + 技能定义），**不**适用于你用本工具处理的任何书籍或文档。
