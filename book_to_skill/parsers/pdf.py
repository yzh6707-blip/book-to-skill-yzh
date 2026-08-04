from __future__ import annotations

import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

# pdfminer runs in-process (no subprocess timeout), so guard it with an explicit
# deadline; a malformed or pathological PDF must not hang the CLI forever.
PDFMINER_TIMEOUT = 120

_PDF_PAGE_NUM = re.compile(r"^\s*(\d{1,4}|[ivxlcdm]{1,7})\s*$", re.IGNORECASE)
# Note: `\w+` (not `\w`) so a wrapped compound like "well-\nknown" captures the
# whole word on each side; single-character groups could never match the
# dictionary in _dehyphenate and always produced "wellknown".
_PDF_HYPHEN_WRAP = re.compile(r"(\w+)-\n(\w+)")

# Hyphenated compounds that are real words and must NOT be merged when a line
# wrap splits them ("well-\nknown" is "well-known", not "wellknown"). Everything
# else still dehyphenates ("informa-\ntion" -> "information").
_HYPHEN_COMPOUNDS = frozenset(
    """
    all-time best-known built-in close-knit cost-effective cross-platform
    decision-making end-user fast-paced first-hand free-market full-time
    good-looking high-level high-quality high-speed human-readable in-depth
    low-cost low-level machine-readable off-the-shelf old-fashioned open-ended
    open-source part-time real-time self-contained self-service short-term
    state-owned step-by-step time-consuming top-level up-to-date user-friendly
    well-being well-known well-defined well-designed
    """.split()
)


def _dehyphenate(text: str) -> str:
    """Rejoin hyphenated line-wraps unless the compound is a real hyphenated word."""

    def _repl(m: re.Match) -> str:
        left, right = m.group(1), m.group(2)
        if (left + "-" + right).lower() in _HYPHEN_COMPOUNDS:
            return left + "-" + right
        return left + right

    return _PDF_HYPHEN_WRAP.sub(_repl, text)


def clean_pdftotext(text: str) -> str:
    """Clean pdftotext '-layout' output (pages are form-feed delimited): drop
    repeated running headers/footers and edge page numbers, and join words split
    across a line by a hyphen."""
    pages = text.split("\f")
    if len(pages) >= 3:
        # A top/bottom line repeated on > half the pages is boilerplate.
        edge = Counter()
        for p in pages:
            nb = [ln.strip() for ln in p.splitlines() if ln.strip()]
            if nb:
                edge[nb[0]] += 1
                edge[nb[-1]] += 1
        boiler = {ln for ln, c in edge.items() if c > len(pages) / 2}
        kept = []
        for p in pages:
            lines = p.splitlines()
            nb_idx = [i for i, ln in enumerate(lines) if ln.strip()]
            first = nb_idx[0] if nb_idx else None
            last = nb_idx[-1] if nb_idx else None
            for i, ln in enumerate(lines):
                s = ln.strip()
                if s in boiler:
                    continue
                # Drop a bare page number only at a page edge (varies per page).
                if i in (first, last) and _PDF_PAGE_NUM.match(s):
                    continue
                kept.append(ln)
        text = "\n".join(kept)
    else:
        text = text.replace("\f", "\n")
    # ponytail: naive dehyphenation; may join a genuinely-hyphenated wrapped
    # compound ("well-\nknown" -> "wellknown"). Dictionary-aware split if it bites.
    return _dehyphenate(text)


def extract_with_pdftotext(pdf_path: str) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    try:
        pdf_path = os.path.abspath(pdf_path)
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
        if result.returncode == 0 and result.stdout.strip():
            return clean_pdftotext(result.stdout)
    except Exception as e:
        print(f"  [warn] extract_with_pdftotext failed: {type(e).__name__}: {e}", file=sys.stderr)
    return None


def extract_with_pypdf(pdf_path: str) -> str | None:
    try:
        import pypdf
        text_parts = []
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception:
                    text_parts.append("")
        return "\n".join(text_parts)
    except ImportError:
        return None
    except Exception as e:
        print(f"  [warn] extract_with_pypdf failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def extract_with_pdfminer(pdf_path: str) -> str | None:
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        return None
    # Run extraction on a worker thread so we can enforce a deadline. The worker
    # may keep running after a timeout (threads cannot be killed), but the CLI
    # proceeds to the next extractor / book; `wait=False` avoids a shutdown hang.
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(extract_text, pdf_path)
        return future.result(timeout=PDFMINER_TIMEOUT)
    except concurrent.futures.TimeoutError:
        print(
            f"  [warn] extract_with_pdfminer timed out after {PDFMINER_TIMEOUT}s — "
            "file may be malformed",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(f"  [warn] extract_with_pdfminer failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    finally:
        pool.shutdown(wait=False)


def extract_with_docling(pdf_path: str) -> str | None:
    """Layout-aware extraction using Docling. Best for technical books with tables and code."""
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import PdfFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        result = converter.convert(pdf_path)
        return result.document.export_to_markdown()
    except ImportError:
        return None
    except Exception as e:
        print(f"  [warn] extract_with_docling failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def extract_with_ocr(pdf_path: str, lang: str | None = None) -> str | None:
    """OCR a scanned (textless) PDF via pdftoppm (poppler) + tesseract.

    Returns None if either binary is missing or the OCR run fails, so callers
    can fall back gracefully. Language defaults to tesseract's ``eng`` and can
    be overridden with the ``BOOK_SKILL_OCR_LANG`` env var, e.g.
    ``eng+chi_sim`` for Chinese scanned books.
    """
    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        return None
    lang = lang or os.environ.get("BOOK_SKILL_OCR_LANG", "eng")
    try:
        pdf_path = os.path.abspath(pdf_path)
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "page")
            result = subprocess.run(
                ["pdftoppm", "-png", "-r", "300", pdf_path, base],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode != 0:
                print(f"  [warn] pdftoppm failed: {result.stderr.strip()}", file=sys.stderr)
                return None
            images = sorted(Path(tmp).glob("page-*.png"))
            if not images:
                print("  [warn] pdftoppm produced no page images", file=sys.stderr)
                return None
            parts = []
            for img in images:
                r = subprocess.run(
                    ["tesseract", str(img), "stdout", "-l", lang],
                    capture_output=True, text=True, timeout=180,
                    encoding="utf-8", errors="replace",
                )
                if r.returncode == 0 and r.stdout.strip():
                    parts.append(r.stdout.strip())
            return "\n\n".join(parts) if parts else None
    except Exception as e:
        print(f"  [warn] extract_with_ocr failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def count_pages(pdf_path: str) -> int:
    # Try pdfinfo first
    if shutil.which("pdfinfo"):
        try:
            pdf_path = os.path.abspath(pdf_path)
            result = subprocess.run(
                ["pdfinfo", pdf_path], capture_output=True, text=True, timeout=15
            )
            for line in result.stdout.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split(":")[1].strip())
        except Exception:
            pass
    # Fallback: count pages with pypdf
    try:
        import pypdf
        with open(pdf_path, "rb") as f:
            return len(pypdf.PdfReader(f).pages)
    except Exception:
        return 0
