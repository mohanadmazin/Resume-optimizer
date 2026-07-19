"""Post-processing for AI-generated text — context-aware cleaning."""
import json
import re

# Patterns for markdown formatting
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"__(.+?)__")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_HTML_TAG_RE = re.compile(r"</?(?:b|em|strong|i|u|span|div|p|br|hr)[^>]*>", re.I)

# Thinking block pattern (qwen3, deepseek-r1, etc.)
_THINKING_RE = re.compile(r"<think>.*?</think>", re.S)

# Pipe-delimited table row
_TABLE_ROW_RE = re.compile(r"^\|.*\|$", re.M)

# Fenced code block
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.M)


class PostProcessor:
    """Context-aware text cleaning for AI-generated resume content."""

    def clean_for_resume(self, text: str) -> str:
        """Strip AI formatting while preserving structure.

        Unlike the old naive clean_ai_text(), this preserves:
        - Pipe-delimited tables
        - Fenced code blocks
        - Legitimate inline formatting context
        """
        if not text:
            return ""

        # Remove thinking blocks first
        text = _THINKING_RE.sub("", text)

        # Split into protected (code blocks, tables) and unprotected regions
        protected: list[str] = []

        def _protect(match: re.Match) -> str:
            placeholder = f"\x00PROTECTED{len(protected)}\x00"
            protected.append(match.group(0))
            return placeholder

        # Protect fenced code blocks
        text = _CODE_BLOCK_RE.sub(_protect, text)

        # Protect table rows (keep entire table intact)
        text = _TABLE_ROW_RE.sub(_protect, text)

        # Now safe to strip formatting from unprotected text
        text = _strip_formatting(text)

        # Restore protected regions
        for i, original in enumerate(protected):
            text = text.replace(f"\x00PROTECTED{i}\x00", original)

        return text.strip()

    def clean_for_json(self, text: str) -> str:
        """Light cleaning for JSON mode — strip thinking blocks only."""
        text = _THINKING_RE.sub("", text)
        return text.strip()

    def extract_json(self, text: str) -> dict:
        """Extract a JSON object from potentially malformed AI output.

        Tries direct parse first, then falls back to extracting the outermost
        braces. Input is expected to be already cleaned of thinking blocks.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        return {}


def _strip_formatting(text: str) -> str:
    """Remove markdown bold, italic, inline code, and HTML tags."""
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _HTML_TAG_RE.sub("", text)
    return text
