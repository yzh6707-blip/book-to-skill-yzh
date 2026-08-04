from __future__ import annotations

import posixpath
import re
import zipfile
import sys
from book_to_skill.parsers.html import _HTMLTextExtractor


def extract_with_ebooklib(epub_path: str) -> str | None:
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup

        book = epub.read_epub(epub_path)
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        # ebooklib iterates the manifest, NOT the reading order, so a publisher
        # that lists chapters out of order in the manifest gets scrambled text.
        # Resolve the OPF spine ourselves and order by it — the same ordering
        # the stdlib zipfile fallback uses, so both paths agree.
        items_by_name = {item.get_name(): item for item in items}
        parts: list[str] = []
        seen: set[str] = set()
        for href in _parse_spine_hrefs(epub_path):
            item = items_by_name.get(href)
            if item and href not in seen:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                parts.append(soup.get_text(separator="\n"))
                seen.add(href)
        # Safety net: any content document not listed in the spine (e.g. a nav
        # doc) is appended at the end so nothing is silently dropped.
        for item in items:
            name = item.get_name()
            if name not in seen:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                parts.append(soup.get_text(separator="\n"))
                seen.add(name)
        return "\n\n".join(parts) if parts else None
    except ImportError:
        return None
    except Exception as e:
        print(f"  [warn] extract_with_ebooklib failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def _parse_spine_hrefs(epub_path: str) -> list[str]:
    """Resolve the OPF spine into an ordered list of content-doc hrefs.

    Returns manifest hrefs in true reading order (spine ``<itemref>`` order,
    with relative hrefs resolved against the OPF's own directory), then appends
    any manifest content documents not listed in the spine as a safety net so
    nothing is lost. Returns ``[]`` when the archive has no usable OPF.
    """
    try:
        with zipfile.ZipFile(epub_path) as zf:
            opf_path = _find_opf_path(zf)
            if not opf_path:
                return []
            opf_dir = posixpath.dirname(opf_path)
            opf_text = zf.read(opf_path).decode("utf-8", errors="replace")

            # Manifest: item id -> resolved href. Parse each <item> opening tag
            # so attribute order (id before/after href) does not matter; both
            # self-closing <item .../> and <item ...></item> forms work because
            # all attributes live in the opening tag.
            manifest: dict[str, str] = {}
            for item_tag in re.findall(r"<item\b[^>]*?/?>", opf_text):
                id_m = re.search(r'\bid=["\']([^"\']+)["\']', item_tag)
                href_m = re.search(r'\bhref=["\']([^"\']+)["\']', item_tag)
                if id_m and href_m:
                    href = href_m.group(1)
                    resolved = posixpath.normpath(posixpath.join(opf_dir, href)) if opf_dir else href
                    manifest[id_m.group(1)] = resolved

            ordered: list[str] = []
            seen: set[str] = set()
            for idref in re.findall(r'<itemref\b[^>]*?\bidref=["\']([^"\']+)["\']', opf_text):
                href = manifest.get(idref)
                if href and href not in seen:
                    ordered.append(href)
                    seen.add(href)

            # Safety net: append remaining manifest content documents (e.g. a
            # nav doc not in the spine) in manifest order.
            for href in manifest.values():
                if href.endswith((".html", ".xhtml")) and href not in seen:
                    ordered.append(href)
                    seen.add(href)
            return ordered
    except Exception:
        return []


def _find_opf_path(zf: zipfile.ZipFile) -> str | None:
    """Locate the OPF package document inside an EPUB archive.

    First tries ``META-INF/container.xml`` (the spec-defined entry point),
    then falls back to scanning the archive for any ``.opf`` file.
    """
    # Spec-defined: read container.xml for the rootfile path
    try:
        container = zf.read("META-INF/container.xml").decode("utf-8", errors="replace")
        match = re.search(r'full-path=["\']([^"\']+\.opf)["\']', container)
        if match:
            return match.group(1)
    except (KeyError, Exception):
        pass

    # Fallback: glob for any .opf file
    opf_files = [n for n in zf.namelist() if n.endswith(".opf")]
    return opf_files[0] if opf_files else None


def extract_with_zipfile(epub_path: str) -> str | None:
    """stdlib-only EPUB extractor: unzip → parse HTML files in spine order."""
    try:
        with zipfile.ZipFile(epub_path) as zf:
            names = zf.namelist()

            # True reading order comes from the OPF spine (shared with the
            # ebooklib path); fall back to sorted content docs with no OPF.
            spine_order = _parse_spine_hrefs(epub_path)
            html_files = spine_order or sorted(
                n for n in names if n.endswith((".html", ".xhtml"))
            )
            if not html_files:
                return None

            parts = []
            for name in html_files:
                try:
                    raw = zf.read(name).decode("utf-8", errors="replace")
                    parser = _HTMLTextExtractor()
                    parser.feed(raw)
                    parts.append(parser.get_text())
                except Exception:
                    continue
            return "\n\n".join(parts) if parts else None
    except Exception as e:
        print(f"  [warn] extract_with_zipfile failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def count_epub_chapters(epub_path: str) -> int:
    """Count spine items (approximate chapter count) without dependencies."""
    try:
        with zipfile.ZipFile(epub_path) as zf:
            opf_path = _find_opf_path(zf)
            if not opf_path:
                return 0
            opf_text = zf.read(opf_path).decode("utf-8", errors="replace")
            return len(re.findall(r'<itemref\b', opf_text))
    except Exception:
        return 0

