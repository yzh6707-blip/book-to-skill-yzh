"""Tests for the generated-skill structural validator (tools/validate_generated.py)."""

import importlib.util
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
spec = importlib.util.spec_from_file_location(
    "validate_generated",
    TOOLS_DIR / "validate_generated.py",
)
validator = importlib.util.module_from_spec(spec)
sys.modules["validate_generated"] = validator
spec.loader.exec_module(validator)


def _write_skill(
    root: Path,
    *,
    name: str = "ok-skill",
    description: str = "A valid generated skill.",
    index_links: list[str] | None = None,
    chapter_bodies: dict[str, str] | None = None,
) -> Path:
    """Write a skill; chapters/ files and SKILL.md index are configurable."""
    skill = root / name
    (skill / "chapters").mkdir(parents=True)
    chapters = list((chapter_bodies or {}).keys()) or ["ch01-intro.md"]
    default_body = "# Chapter 1: Intro\n\n## Core Idea\nIdea.\n\n## Key Takeaways\n1. x\n"
    for chapter in chapters:
        (skill / "chapters" / chapter).write_text(
            (chapter_bodies or {}).get(chapter, default_body),
            encoding="utf-8",
        )

    links = index_links if index_links is not None else [f"chapters/{c}" for c in chapters]
    index_rows = "\n".join(
        f"| [{i}]({link}) | Title | Framework |" for i, link in enumerate(links)
    )
    (skill / "SKILL.md").write_text(
        f"""---
name: {name}
description: "{description}"
---

# {name}

## Chapter Index

| # | Title | Key Frameworks |
|---|-------|----------------|
{index_rows}
""",
        encoding="utf-8",
    )
    return skill


def test_clean_skill_passes(tmp_path: Path):
    skill = _write_skill(tmp_path)

    errors, warns = validator.validate_generated_skill(skill)

    assert errors == []
    assert warns == []


def test_missing_frontmatter_name_is_error(tmp_path: Path):
    skill = _write_skill(tmp_path, name="bad-name")
    (skill / "SKILL.md").write_text(
        "---\ndescription: no name here\n---\n\n# x\n", encoding="utf-8"
    )

    errors, _ = validator.validate_generated_skill(skill)

    assert any("'name' is required" in e for e in errors)


def test_bad_slug_shape_is_error(tmp_path: Path):
    skill = _write_skill(tmp_path, name="Bad_Name_1")

    errors, _ = validator.validate_generated_skill(skill)

    assert any("must be lowercase" in e for e in errors)


def test_missing_description_is_error(tmp_path: Path):
    skill = _write_skill(tmp_path, name="ok-skill")
    (skill / "SKILL.md").write_text(
        "---\nname: ok-skill\n---\n\n# x\n", encoding="utf-8"
    )

    errors, _ = validator.validate_generated_skill(skill)

    assert any("'description' is required" in e for e in errors)


def test_broken_chapter_index_link_is_error(tmp_path: Path):
    skill = _write_skill(tmp_path, index_links=["chapters/ch99-missing.md"])

    errors, _ = validator.validate_generated_skill(skill)

    assert any("links to missing file: chapters/ch99-missing.md" in e for e in errors)


def test_unreferenced_chapter_file_is_warning(tmp_path: Path):
    skill = _write_skill(tmp_path)
    (skill / "chapters" / "ch02-extra.md").write_text(
        "# Chapter\n\n## Core Idea\nIdea.\n\n## Key Takeaways\n1. x\n",
        encoding="utf-8",
    )

    _, warns = validator.validate_generated_skill(skill)

    assert any("not referenced by SKILL.md Chapter Index" in w for w in warns)


def test_missing_required_chapter_headings_is_error(tmp_path: Path):
    skill = _write_skill(
        tmp_path,
        chapter_bodies={"ch01-intro.md": "# Chapter 1\n\nNo headings here.\n"},
    )

    errors, _ = validator.validate_generated_skill(skill)

    assert any(
        "missing required heading(s): ## Core Idea, ## Key Takeaways" in e
        for e in errors
    )


def test_oversized_core_is_warning(tmp_path: Path, monkeypatch):
    skill = _write_skill(tmp_path)
    monkeypatch.setattr(validator, "SKILL_MD_TOKEN_BUDGET", 1)

    _, warns = validator.validate_generated_skill(skill)

    assert any("design cap 1" in w for w in warns)


def test_grounding_flags_unknown_bolded_term(tmp_path: Path):
    skill = _write_skill(tmp_path)
    (skill / "chapters" / "ch01-intro.md").write_text(
        "# Chapter 1\n\n## Core Idea\nIdea.\n\n## Key Takeaways\n1. x\n\n## Frameworks\n"
        "- **TotallyMadeUpFramework**: apply when X\n",
        encoding="utf-8",
    )
    source = tmp_path / "full_text.txt"
    source.write_text(
        "The book discusses real frameworks and nothing invented here.\n",
        encoding="utf-8",
    )

    _, warns = validator.validate_generated_skill(skill, full_text=source)

    assert any(
        "TotallyMadeUpFramework" in w and "not found verbatim" in w for w in warns
    )


def test_grounding_passes_when_term_present(tmp_path: Path):
    skill = _write_skill(tmp_path)
    (skill / "chapters" / "ch01-intro.md").write_text(
        "# Chapter 1\n\n## Core Idea\nIdea.\n\n## Key Takeaways\n1. x\n\n## Frameworks\n"
        "- **Westrum Model**: apply when Y\n",
        encoding="utf-8",
    )
    source = tmp_path / "full_text.txt"
    source.write_text("The Westrum Model is described in detail.\n", encoding="utf-8")

    _, warns = validator.validate_generated_skill(skill, full_text=source)

    assert not any("not found verbatim" in w for w in warns)


def test_cli_returns_nonzero_on_errors(tmp_path: Path, capsys):
    skill = _write_skill(tmp_path, index_links=["chapters/ch98-ghost.md"])

    assert validator.main([str(skill)]) == 1
    assert "validation failed" in capsys.readouterr().out


def test_cli_returns_zero_for_clean_skill(tmp_path: Path, capsys):
    skill = _write_skill(tmp_path)

    assert validator.main([str(skill)]) == 0
    assert "validation passed" in capsys.readouterr().out


def test_missing_skill_dir_reports_error(tmp_path: Path):
    missing = tmp_path / "does-not-exist"

    errors, warns = validator.validate_generated_skill(missing)

    assert errors and "missing SKILL.md" in errors[0]
    assert warns == []
