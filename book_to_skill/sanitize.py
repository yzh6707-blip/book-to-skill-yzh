from __future__ import annotations


_ZERO_WIDTH_CODEPOINTS = frozenset({0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF})
_TAG_BLOCK_START = 0xE0000
_TAG_BLOCK_END = 0xE007F
# Bidirectional text override / isolate controls (U+202A–U+202E, U+2066–U+2069).
# These render invisible in most UIs but can reverse the visual order of text,
# a documented vector for smuggling instructions or credentials into prompts.
_BIDI_CODEPOINTS = frozenset(
    {
        0x202A, 0x202B, 0x202C, 0x202D, 0x202E,  # LRE / RLE / PDF / LRO / RLO
        0x2066, 0x2067, 0x2068, 0x2069,          # LRI / RLI / FSI / PDI
    }
)


def sanitize_extracted_text(text: str) -> tuple[str, int]:
    """Remove invisible code points used for document-borne prompt injection.

    Covers zero-width characters, the Unicode tag block (used for
    ``lang="..."`` spoofing on some renderers), and the bidi override/isolate
    controls that can reorder visible text without being seen in a diff.
    """
    kept: list[str] = []
    removed = 0

    for character in text:
        codepoint = ord(character)
        if (
            codepoint in _ZERO_WIDTH_CODEPOINTS
            or codepoint in _BIDI_CODEPOINTS
            or _TAG_BLOCK_START <= codepoint <= _TAG_BLOCK_END
        ):
            removed += 1
            continue
        kept.append(character)

    return "".join(kept), removed
