<p align="center">
  <strong>English</strong> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="docs/assets/logo.png" alt="book-to-skill logo" width="120">
</p>

<h1 align="center">book-to-skill</h1>

<p align="center">
  <strong>Turn any technical book, document folder, or collection of sources into a unified agent skill — ready to study, reference, and use while you work in GitHub Copilot CLI, Amp, Claude Code, Trae, or CodeBuddy.</strong>
</p>

<p align="center">
  <a href="https://github.com/yzh6707-blip/book-to-skill-yzh/releases"><img src="https://img.shields.io/github/v/release/yzh6707-blip/book-to-skill-yzh?style=for-the-badge&color=blueviolet" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Agent_Skills-Open_Standard-blueviolet?style=for-the-badge" alt="Agent Skills standard">
  <img src="https://img.shields.io/badge/PDF%20%E2%80%A2%20EPUB%20%E2%80%A2%20DOCX%20%E2%80%A2%20MD%20%E2%80%A2%20HTML%20%E2%80%A2%20RTF%20%E2%80%A2%20MOBI-supported-green?style=for-the-badge" alt="Formats supported">
  <img src="https://img.shields.io/badge/Security-bidi%20%7C%20XXE%20%7C%20injection%20guarded-blue?style=for-the-badge" alt="Security hardened">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License">
</p>

<p align="center">
  <a href="#-why">Why</a> ·
  <a href="#-whats-new">What's new</a> ·
  <a href="#-what-it-generates">What it generates</a> ·
  <a href="#-usage">Usage</a> ·
  <a href="#-requirements">Requirements</a> ·
  <a href="#-how-it-works">How it works</a> ·
  <a href="#-security">Security</a> ·
  <a href="#-faq">FAQ</a> ·
  <a href="#-install">Install</a> ·
  <a href="#-standalone-cli-pip">CLI</a> ·
  <a href="docs/ARCHITECTURE.md">Architecture</a>
</p>

<p align="center">
  <strong>24×–51× fewer tokens than dumping the book into context</strong> to answer one question, measured on real books (<a href="docs/PERFORMANCE.md">how it's measured</a>).
</p>

**How it works, in 3 steps:**

1. **Point** it at a file, folder, or glob — `/book-to-skill ./my-book.pdf`
2. **It distills** the book into a skill — frameworks, decision rules, anti-patterns, and per-chapter files. Structure, not a summary.
3. **Your agent loads it on demand** — ask `/my-book replication` and it reads the right chapter and answers from the real content, no hallucination.

---

## 🤔 Why

You buy a great technical book. You read it once. Three months later you can't remember chapter 7 existed.

The usual workarounds don't help:
- 📄 "Let me just search the PDF" → you get a list of pages, not answers
- 🧠 "I'll ask the agent about this book" → it either hallucinates or says it doesn't have the content
- 📝 "I'll take notes as I read" → you end up with a 200-line doc you never open again

**book-to-skill solves this by turning the book into a structured skill your agent loads on demand.**

Once installed, you just type `/your-book-slug replication` and the agent reads the right chapter and answers from the actual content. No hallucination. No digging through PDFs. The book becomes part of your workflow.

Works with any host that supports the open [Agent Skills](https://github.com/agentskills/agentskills) standard — GitHub Copilot CLI, Amp, Claude Code, Trae, CodeBuddy and WorkBuddy all read the same `SKILL.md` format.

---

## ✨ What's new

This fork hardens and extends the original converter. Everything the original does is preserved; these are the additions:

**Correctness & safety**
- **Bidi prompt-injection defense** — extraction and the generated-skill scanner now strip bidi override/isolate controls (U+202A–U+202E, U+2066–U+2069) alongside zero-width characters, closing a real document-borne injection vector.
- **EPUB reading order fixed** — `ebooklib` iterates the manifest, not the spine, so a publisher listing chapters out of order produced scrambled text while the stdlib fallback was correct. Both paths now share one OPF-spine resolver.
- **DOCX table position preserved** — the `python-docx` path no longer appends all tables after the paragraphs; both extraction paths emit document order.
- **`pdfminer` bounded by a 120s deadline** — a malformed PDF can no longer hang the CLI forever.
- **PDF dehyphenation fixed** — wrapped compounds like `well-\nknown` are kept as `well-known` instead of being mangled into `wellknown`.

**Generated-skill validation (no more unverifiable claims)**
- **`tools/validate_generated.py`** — a structural gate that checks frontmatter, chapter-index link resolution, required chapter headings, token budgets, and **grounding** of bolded terms against the extracted source. Errors are hard failures; it runs in Step 9.5 of the workflow alongside the security scanner.

**Efficiency & DX**
- **Content-hash extraction cache** — unchanged sources are never re-parsed (huge for PDF/docling/OCR and for the fold-in update flow); `--no-cache` forces a full pass.
- **`probe` subcommand** — cross-platform (Windows/PowerShell-friendly) replacement for `wc`/`grep`/`sed`: line/word/token counts, chapter boundaries with line numbers, and `--chapter N` text slices.
- **CJK-aware token estimation** — Chinese/Japanese/Korean text is estimated by character count (~1.5 chars/token) instead of the English word heuristic, which under-counted CJK by 3–4×.
- **Non-interactive mode** — `BOOK_SKILL_ASSUME` / `BOOK_SKILL_ASSUME_DEPTH` / `BOOK_SKILL_NO_PROMPT` let CI and scripted pipelines run the whole flow with no prompts.
- **Concurrency safety** — a PID lock plus stale-file cleanup prevents parallel runs from clobbering the shared work directory.
- **OCR knobs** — per-page average text threshold, plus `BOOK_SKILL_FORCE_OCR` / `BOOK_SKILL_NO_OCR` / `BOOK_SKILL_OCR_THRESHOLD` overrides.

---

## 📦 What it generates

Running `/book-to-skill your-book.pdf` (or a folder, glob, or list of files) creates a full skill in your agent's skills directory (`~/.copilot/skills/<slug>/` for Copilot CLI, `~/.agents/skills/<slug>/` for Amp or cross-agent, `~/.claude/skills/<slug>/` for Claude Code, `~/.codebuddy/skills/<slug>/` for CodeBuddy, `~/.workbuddy/skills/<slug>/` for WorkBuddy):

| File | Purpose | Size |
|------|---------|------|
| `SKILL.md` | Core mental models + chapter index | ~4,000 tokens |
| `chapters/ch01-*.md` … | One file per chapter, loaded on-demand | ~1,000 tokens each |
| `glossary.md` | Every key term, alphabetically sorted with chapter refs | ~1,500 tokens |
| `patterns.md` | All techniques, algorithms, and design patterns | ~2,000 tokens |
| `cheatsheet.md` | Decision tables and quick-reference rules | ~1,000 tokens |

**Chapter files are loaded on-demand** — they don't count against the skill budget until you ask about that topic.

---

## 🚀 Usage

```
/book-to-skill <path-to-document-folder-or-glob>... [skill-name-slug]
```

Supported document formats: PDF, EPUB, DOCX, TXT, Markdown, reStructuredText, AsciiDoc, HTML, RTF, MOBI/AZW/AZW3.

**Examples:**

```bash
# Process several files together into a unified skill
/book-to-skill ~/papers/paper1.pdf ~/notes/export.txt unified-research

# Process all supported files in a folder together
/book-to-skill ~/workspace/project-docs/ project-knowledge

# Process files matching a glob pattern
/book-to-skill "~/books/*.epub" my-library

# Update/fold new material into an existing skill folder
/book-to-skill ~/articles/new-paper.pdf ~/.claude/skills/project-knowledge
```

**Non-interactive / CI runs** — answer the book-type and depth questions via environment variables instead of prompts:

```bash
BOOK_SKILL_ASSUME=technical BOOK_SKILL_ASSUME_DEPTH=study BOOK_SKILL_NO_PROMPT=1 \
  /book-to-skill ./my-book.pdf
```

After the skill is created, use it like any other agent skill:

```bash
/designing-data-intensive-apps                  # load core mental models
/designing-data-intensive-apps replication      # find and explain a topic
/designing-data-intensive-apps ch05             # dive into chapter 5
/designing-data-intensive-apps "what chapters do you have?"
```

In GitHub Copilot CLI you may need to run `/skills reload` after the file is written so the new skill appears in `/skills list`. Claude Code, Amp, Trae, CodeBuddy and WorkBuddy pick it up on the next session.

---

## 🔧 Requirements

The extractor tries tools in order per format and uses the first available. If nothing is installed, it tells you which command to run. Plain text, Markdown, reStructuredText and AsciiDoc need no extra deps.

> **Check your setup in one command:** `python3 -m book_to_skill --check` prints which extractors are installed for every format and the exact command to install anything missing — no file needed.

**PDF — choose by book type:**

| Book type | Tool | Install | Speed |
|-----------|------|---------|-------|
| Text-heavy (prose, few tables) | `pdftotext` (poppler) | `sudo apt install poppler-utils` | ⚡ instant |
| Text-heavy fallback | `pypdf` | `pip3 install pypdf` | ⚡ instant |
| Text-heavy fallback | `pdfminer.six` | `pip3 install pdfminer.six` | ⚡ instant |
| **Technical (code, tables, formulas)** | **`docling`** | `pip3 install docling` | ~1.5s/page |
| **Scanned (no text layer)** | `tesseract` + `pdftoppm` | `sudo apt install tesseract-ocr poppler-utils` | slow, automatic |

> Before extraction begins, the skill asks you whether the book is **technical** or **text-heavy** and picks the right tool automatically. Docling preserves markdown tables and code blocks; pdftotext is faster for prose-only books. A PDF with a thin text layer (per-page average below ~30 chars) is treated as a scan and OCR is attempted automatically — disable with `BOOK_SKILL_NO_OCR=1`, force with `BOOK_SKILL_FORCE_OCR=1`.

**EPUB:**

| Tool | Install | Quality |
|------|---------|---------|
| `ebooklib` + `beautifulsoup4` | `pip3 install ebooklib beautifulsoup4` | ⭐⭐⭐ Best |
| stdlib `zipfile` | built-in — no install needed | ⭐⭐ Always available |

**Other formats:**

| Format | Tool | Install |
|--------|------|---------|
| DOCX | `python-docx` (fallback: stdlib ZIP/XML) | `pip3 install python-docx` |
| HTML | `beautifulsoup4` (fallback: stdlib `html.parser`) | `pip3 install beautifulsoup4` |
| RTF | `striprtf` (fallback: regex) | `pip3 install striprtf` |
| MOBI / AZW / AZW3 | Calibre `ebook-convert` (external app, not pip) | https://calibre-ebook.com/download |
| TXT / Markdown / reStructuredText / AsciiDoc | built-in | — |

---

## ⚙️ How it works

```
One file · a folder · a glob · a list of paths
     │
     ▼
Step 1.5 — "Technical or text-heavy book?"   (or BOOK_SKILL_ASSUME=… for CI)
     │
     ├── technical → Docling  (tables + code blocks as markdown, ~1.5s/page)
     └── text      → pdftotext → pypdf → pdfminer  (instant)
     │
     ▼
book_to_skill <paths…> --mode <technical|text>
  per source: PDF → pdftotext/Docling/OCR · EPUB → ebooklib → stdlib zipfile
               (one bad source is skipped with a warning; the rest still process)
  content-hash cache: unchanged sources are reused, not re-parsed
     │
     ├── <workdir>/full_text.txt   (all sources merged, with source markers)
     └── <workdir>/metadata.json   (aggregated stats + per-source array, incl. sha256)
               │
               ▼
          Agent analyzes structure
          (title, author, chapters, ToC — spanning all sources)
          ── or, if targeting an existing skill: folds new content in (Mode 4)
               │
               ▼
          Generates per-chapter summaries  (800–1,200 tokens each)
          technical → includes Code Examples + Reference Tables sections
          Generates glossary, patterns, cheatsheet
          Generates master SKILL.md with core mental models
               │
               ▼
Step 9.5 — Validation gates (both must pass):
  1. validate_generated.py  → frontmatter, chapter links, headings, budgets, grounding
  2. scan_generated_skill.py → prompt-injection / authority scan
               │
               ▼
          Skill written to one of:
            ~/.copilot/skills/<slug>/     ~/.agents/skills/<slug>/
            ~/.claude/skills/<slug>/       ~/.codebuddy/skills/<slug>/
            ~/.workbuddy/skills/<slug>/
          <workdir>/                       🗑️  cleaned up (cache/ retained)
```

**Extraction benchmark** (103-page technical book, CPU only):

| Method | Time | Tokens | Tables | Code blocks |
|--------|------|--------|--------|-------------|
| pdftotext | 0.1s | 27K | 0 | 0 |
| Docling | 164s | 27K (+1.2%) | 48 | 36 |

**Real conversions** (measured: pages, extracted tokens, chapters auto-detected,
estimated one-pass cost on Claude Sonnet 4.5 at \$3/\$15 per MTok):

| Book | Format | Pages | Tokens | Chapters | ~Cost |
|------|--------|------:|-------:|---------:|------:|
| Think Python 2 | PDF | 244 | 119K | 19 | \$0.88 |
| Working Backwards | PDF | 371 | 175K | 10 | \$0.96 |
| Pro Git | PDF | 501 | 229K | — † | \$1.23 |
| Moby-Dick | EPUB | — | 301K | — † | \$1.42 |

† Chapter auto-detection needs explicit `Chapter N` / `Capítulo N` headings. Pro Git
uses section titles and Moby-Dick uses chapter *titles* / roman numerals, so neither
auto-segments — extraction and conversion still work, but you point at sections
manually. A full skill costs roughly **\$1 per book**; far less than re-reading the
PDF every session.

<details>
<summary>Design principles (click to expand)</summary>

1. **Density over completeness** — a 1,000-token summary beats a 10,000-token excerpt
2. **Practitioner voice** — "Use X when Y", not "The book explains X"
3. **Front-loaded SKILL.md** — compaction keeps the first ~5,000 tokens; the most important content comes first
4. **On-demand chapters** — the topic index tells Claude which file to read; chapters load only when needed
5. **Never raw text** — always synthesize, summarize, extract signal from the source
6. **Groundable output** — bolded framework names must appear in the source text; `validate_generated.py` enforces it

</details>

---

## 🛡️ Security

Document-borne prompt injection is taken seriously. The pipeline defends at three layers:

1. **Extraction** (`book_to_skill/sanitize.py`) — removes invisible code points used for smuggling: zero-width characters, the Unicode tag block, and bidi override/isolate controls (U+202A–U+202E, U+2066–U+2069) that can reverse the visible order of text without appearing in a diff.
2. **Generation spec** (`SKILL.md`) — instructs the agent to treat source text as data, never as instructions, and to flag suspicious directives.
3. **Post-generation scan** (`tools/scan_generated_skill.py`) — audits the finished skill for leftover invisible characters and authority/injection patterns; runs as a hard gate in Step 9.5, together with `tools/validate_generated.py`.

Other hardening: DOCX/EPUB extraction is XML-entity-safe (no XXE), subprocess invocations never use a shell, and per-source failures are contained (a bad file is skipped, the batch continues).

---

## ❓ FAQ

**"Can't I just dump the PDF/EPUB into my Claude project context?"**

You can — but every conversation will burn that token budget upfront. A 400-page book is ~200K tokens. With a skill, only the chapters relevant to your question load — typically a SKILL.md core (~4K) plus the one chapter you asked about (~1K). The rest stays on disk until you need it.

The economics are amortization, not size. Pasting the book pays the full token bill **on every turn of every session, forever**. book-to-skill pays the extraction cost **once** and every future conversation loads only the slice it needs.

More importantly: raw text injection is retrieval. A skill is reasoning. When you load a chapter file, Claude isn't searching for keyword matches — it's working with pre-extracted named frameworks, principles, and mental models structured for application, not for reading.

---

**"Claude has a 1M-token context window now — can't I just keep the whole book loaded?"**

A bigger window changes what *fits*, not what's *smart*:

- **You pay per token, per call.** The skill loads kilobytes, not megabytes.
- **Recall degrades with fill.** A 1K curated chapter beats 200K of raw prose for answering one question.
- **Window ≠ structure.** The skill ships pre-extracted frameworks — reasoning, not retrieval.

Use the big window for a one-off pass over material you'll never need again. Use a skill for knowledge you'll reach for repeatedly.

---

**"Isn't this just RAG?"**

RAG works at query time: chunk the book → embed everything → find similar vectors → inject into prompt. book-to-skill works at compile time: one deep analysis run extracts the author's actual frameworks, names them, describes when to use each, captures the anti-patterns.

- **Wide and shallow** — a library of dozens of books, "find the part that mentions X" → a RAG tool wins.
- **Narrow and deep** — one book or a tight cluster of related sources, frameworks you apply while you work → book-to-skill wins.

They're complementary: RAG indexes a shelf, book-to-skill masters a spine.

---

**"Popular books are already in Claude's training data. Why bother?"**

For widely-known books, Claude has general knowledge — but it's compressed, averaged across the entire internet's discussion, and may hallucinate specific quotes or chapter locations. book-to-skill works from your actual copy, and the generated skill is now **grounding-checked**: every bolded framework name must appear verbatim in your source text, so the output can't silently invent frameworks.

It also shines for books Claude doesn't know at all: niche technical references, internal company documentation, recent publications, translated works.

---

## 📥 Install

> **Two ways to use it, do not confuse them:**
> - **As an agent skill** (the `/book-to-skill` command in Claude Code, Copilot CLI, Amp, Trae, CodeBuddy or WorkBuddy) → **`git clone` into your skills folder** (below). This is what gives you the slash command and the full convert-a-book flow.
> - **As a standalone CLI** (just the text extractor) → `pip install book-to-skill`, then `book-to-skill --help`. This does **not** register the agent skill; it only installs the extraction engine. See [the CLI section](#-standalone-cli-pip).

The skill follows the open [Agent Skills](https://github.com/agentskills/agentskills) standard, so a single install works for any compatible host.

**GitHub Copilot CLI** (personal skill):

```bash
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.copilot/skills/book-to-skill
# then, in a `copilot` session:
/skills reload
/skills info book-to-skill
```

Or the cross-agent path that Copilot CLI and Amp both discover:

```bash
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.agents/skills/book-to-skill
```

**Claude Code:**

```bash
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.claude/skills/book-to-skill
```

**Trae / CodeBuddy / WorkBuddy** — same standard, different folders:

```bash
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.trae/skills/book-to-skill    # or the workspace's .trae/skills/
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.codebuddy/skills/book-to-skill
git clone https://github.com/yzh6707-blip/book-to-skill-yzh.git ~/.workbuddy/skills/book-to-skill
```

Then in any agent session:

```bash
/book-to-skill ~/path/to/your-book.pdf
# or
/book-to-skill ~/path/to/your-book.epub
```

---

## 🧰 Standalone CLI (pip)

`pip install book-to-skill` is a **separate, optional** path. It installs only the
text-extraction engine as a CLI, for scripting or to grab the optional extractors;
it does **not** register the `/book-to-skill` agent skill (use the `git clone` above
for that).

```bash
pip install "book-to-skill[pdf,epub,docx]"   # engine + optional extractors
book-to-skill ~/path/to/book.pdf --mode text  # or: python -m book_to_skill ...
book-to-skill --check                          # report which extractors are installed
book-to-skill probe book.pdf                   # counts + chapter map with line numbers
book-to-skill probe book.pdf --chapter 3       # just chapter 3's text (Windows-safe sed)
book-to-skill book.pdf --no-cache              # force re-extraction (default: content-hash cache)
```

Extraction is **cached by content SHA-256** (`<workdir>/cache/`): re-running on
unchanged sources skips parsing entirely — useful for the Update/Fold-in flow
and for slow PDF/docling/OCR extraction. `--no-cache` forces a full pass.
Parallel runs are protected by a work-directory lock.

---

## 📁 Repository structure

```
book-to-skill/
├── SKILL.md                 # Skill definition + step-by-step instructions (the generator spec)
├── book_to_skill/           # Modular extraction package
│   ├── cli.py               # Console entrypoint
│   ├── config.py            # Extensions, paths, dependency constants
│   ├── dependencies.py      # Optional-dep probing + --check
│   ├── exceptions.py        # ExtractionError (per-source failures, batch-safe)
│   ├── sanitize.py          # Zero-width / tag-block / bidi prompt-injection stripping
│   ├── utils.py             # CLI parsing, multi-source resolution, chapter detection,
│   │                        # content-hash cache, workdir lock, probe subcommand
│   └── parsers/             # pdf, epub, docx, html, rtf, calibre, text
├── tools/
│   ├── discovery_tax.py         # measures token cost vs context-dump / discovery loop
│   ├── validate_skill.py        # checks a generated SKILL.md against host rules (--lens …)
│   ├── validate_generated.py    # structural gate: links, headings, budgets, grounding
│   └── scan_generated_skill.py  # prompt-injection scan of a generated skill
├── tests/                   # pytest suite (extraction, detection, cache, probe, security)
├── docs/
│   ├── PERFORMANCE.md       # measured benchmarks, discovery tax, cost
│   └── ARCHITECTURE.md      # pipeline + component map
├── CHANGELOG.md             # release history (semver)
├── CONTRIBUTING.md          # dev setup, PR conventions, release process
├── SECURITY.md              # vulnerability reporting
└── README.md                # This file
```

---

## ⚖️ Copyright & fair use

book-to-skill ships **no book content** — not a single page. It's a converter you point at files you already own.

- **Processing is local.** Extraction and analysis run on your machine. Your files are never uploaded by this tool. (If your agent's model runs in the cloud, the text you feed it follows that provider's normal data terms — same as any prompt.)
- **You use your own copy.** Bring a book you bought, docs your company owns, or papers you have the right to read.
- **The output is your notes.** A generated skill is a structured, synthesized derivative — framework names, definitions, takeaways — not a reproduction of the text. The skill explicitly never copies raw passages (see Quality Rule #7). Treat it like handwritten study notes: yours, for personal use.
- **Don't redistribute.** Publishing or sharing a generated skill of a copyrighted work can infringe the rights holder. Keep skills of third-party books private. Internal docs, your own writing, and openly-licensed material are fine to share within the bounds of their license.

When in doubt, follow the license or terms of the source document. This project is a tool; how you use it is on you.

---

## License

MIT — applies to the converter (code + skill definition) in this repository, **not** to any book or document you process with it.
