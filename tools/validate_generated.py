#!/usr/bin/env python3
"""Validate a generated book skill: structure, links, budgets, and grounding.

Checks the artifacts produced by the SKILL.md generator (Steps 7-9) that the
security scanner (``scan_generated_skill.py``) does not cover:

  * SKILL.md frontmatter (``name`` / ``description`` present, slug-shaped name)
  * Chapter Index links resolve to files on disk, and every chapter file is
    referenced by the index (guards against hallucinated links)
  * Every chapter file contains the required template headings
  * Token budgets (SKILL.md core, per-chapter, supporting files)
  * Grounding: framework/term names bolded in chapters should appear in the
    extracted source text (guards against hallucinated frameworks)

Errors are hard failures for the generation run; warnings are advisory (rules
are deliberately broad and may produce false positives — review in context).

Usage: python3 tools/validate_generated.py <skill-dir> [--full-text <path>]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

# Force UTF-8 stdout/stderr so the ✓ / ✗ glyphs don't raise UnicodeEncodeError
# on Windows consoles that default to a legacy code page (e.g. GBK / cp936).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# Token-budget design caps from SKILL.md (Steps 7-9). Chapters are the most
# variable (the Step 7 matrix ranges 800-3,000 depending on BOOK_TYPE x DEPTH),
# so the gate uses a generous ceiling and reports the number rather than
# failing hard.
SKILL_MD_TOKEN_BUDGET = 4000
CHAPTER_TOKEN_CEILING = 4000
SUPPORTING_TOKEN_BUDGETS = {
    "glossary.md": 1500,
    "patterns.md": 2000,
    "cheatsheet.md": 1200,
}

REQUIRED_CHAPTER_HEADINGS = ("## Core Idea", "## Key Takeaways")
CHAPTER_INDEX_PATTERN = re.compile(r"\]\((chapters/[A-Za-z0-9_./-]+\.md)\)")
BOLD_TERM_PATTERN = re.compile(r"\*\*([^*\n]{3,80})\*\*")


def _estimate_tokens(text: str) -> int:
    """Reuse the extractor's CJK-aware estimator when importable."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from book_to_skill.utils import estimate_tokens

        return estimate_tokens(text)
    except Exception:
        cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff")
        if text and cjk / len(text) > 0.3:
            return int(len(text) / 1.5)
        return int(len(text.split()) / 0.75)


def _parse_frontmatter(text: str) -> dict:
    fm = {}
    if not text.startswith("---"):
        return fm
    end = text.find("\n---", 3)
    if end == -1:
        return fm
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line.strip())
        if m:
            fm[m.group(1).lower()] = m.group(2).strip().strip('"').strip("'")
    return fm


def validate_generated_skill(
    skill_dir: Path, full_text: Path | None = None
) -> tuple[list[str], list[str]]:
    """Validate a generated skill. Returns (errors, warnings)."""
    errors: list[str] = []
    warns: list[str] = []

    skill_dir = skill_dir.expanduser()
    master = skill_dir / "SKILL.md"
    if not master.is_file():
        return [f"missing SKILL.md in {skill_dir}"], []

    text = master.read_text(encoding="utf-8")

    # ── Frontmatter ──────────────────────────────────────────────────────────
    fm = _parse_frontmatter(text)
    if not fm:
        errors.append("SKILL.md has no YAML frontmatter (--- block)")
    else:
        name = fm.get("name")
        if not name:
            errors.append("SKILL.md frontmatter: 'name' is required")
        elif not re.fullmatch(r"[a-z0-9-]+", name):
            errors.append(
                f"SKILL.md frontmatter: name '{name}' must be lowercase "
                "letters/digits/hyphens"
            )
        if not fm.get("description"):
            errors.append("SKILL.md frontmatter: 'description' is required")

    # ── Core budget ──────────────────────────────────────────────────────────
    core_tokens = _estimate_tokens(text)
    if core_tokens > SKILL_MD_TOKEN_BUDGET:
        warns.append(
            f"SKILL.md is ~{core_tokens} tokens (design cap {SKILL_MD_TOKEN_BUDGET})"
        )

    # ── Chapter Index links ──────────────────────────────────────────────────
    chapters_dir = skill_dir / "chapters"
    chapter_files = sorted(chapters_dir.glob("ch*.md")) if chapters_dir.is_dir() else []
    index_links = CHAPTER_INDEX_PATTERN.findall(text)
    for link in index_links:
        if not (skill_dir / link).is_file():
            errors.append(f"SKILL.md Chapter Index links to missing file: {link}")
    referenced = set(index_links)
    for chapter in chapter_files:
        rel = f"chapters/{chapter.name}"
        if rel not in referenced:
            warns.append(f"chapter file not referenced by SKILL.md Chapter Index: {rel}")

    # ── Per-chapter template headings + budget ───────────────────────────────
    for chapter in chapter_files:
        body = chapter.read_text(encoding="utf-8")
        missing = [h for h in REQUIRED_CHAPTER_HEADINGS if h not in body]
        if missing:
            errors.append(
                f"{chapter.name}: missing required heading(s): {', '.join(missing)}"
            )
        tokens = _estimate_tokens(body)
        if tokens > CHAPTER_TOKEN_CEILING:
            warns.append(
                f"{chapter.name}: ~{tokens} tokens exceeds the "
                f"{CHAPTER_TOKEN_CEILING} ceiling"
            )

    # ── Supporting-file budgets ──────────────────────────────────────────────
    for filename, budget in SUPPORTING_TOKEN_BUDGETS.items():
        supporting = skill_dir / filename
        if supporting.is_file():
            tokens = _estimate_tokens(supporting.read_text(encoding="utf-8"))
            if tokens > budget:
                warns.append(
                    f"{filename}: ~{tokens} tokens (design cap {budget})"
                )

    # ── Grounding: bolded terms must appear in the source text ───────────────
    if full_text is not None:
        source_path = full_text.expanduser()
        if not source_path.is_file():
            warns.append(f"--full-text path not found: {full_text}")
        else:
            source_lower = source_path.read_text(
                encoding="utf-8", errors="ignore"
            ).lower()
            for chapter in chapter_files:
                body = chapter.read_text(encoding="utf-8")
                for term in BOLD_TERM_PATTERN.findall(body):
                    if term.lower() not in source_lower:
                        warns.append(
                            f"{chapter.name}: bolded term '{term}' not found "
                            "verbatim in source text (may be a synthesized "
                            "framework name or a rewrite — verify)"
                        )

    return errors, warns


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "skill_dir", help="Generated skill directory (contains SKILL.md)"
    )
    parser.add_argument(
        "--full-text",
        help="Path to the extractor's full_text.txt for grounding checks",
    )
    args = parser.parse_args(argv)

    errors, warns = validate_generated_skill(
        Path(args.skill_dir), Path(args.full_text) if args.full_text else None
    )

    for warning in warns:
        print(f"  WARN  {warning}")
    for error in errors:
        print(f"  ERROR {error}")
    if errors:
        print(
            f"✗ generated-skill validation failed: {len(errors)} error(s), "
            f"{len(warns)} warning(s)"
        )
        return 1
    if warns:
        print(
            f"✓ generated-skill validation passed with {len(warns)} advisory "
            "warning(s)"
        )
        return 0
    print("✓ generated-skill validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
