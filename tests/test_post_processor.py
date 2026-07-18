"""Tests for PostProcessor — context-aware AI text cleaning."""
import pytest

from app.ai.post_processor import PostProcessor


@pytest.fixture()
def pp():
    return PostProcessor()


class TestCleanForResume:
    def test_strips_bold_markdown(self, pp):
        assert pp.clean_for_resume("Hello **world**") == "Hello world"

    def test_strips_italic_markdown(self, pp):
        assert pp.clean_for_resume("Hello __world__") == "Hello world"

    def test_strips_inline_code(self, pp):
        assert pp.clean_for_resume("Use `pip install` to install") == "Use pip install to install"

    def test_strips_html_tags(self, pp):
        assert pp.clean_for_resume("<b>Bold</b> and <i>italic</i>") == "Bold and italic"

    def test_removes_thinking_blocks(self, pp):
        text = "<think>Let me think...</think>\nThe answer is 42"
        assert pp.clean_for_resume(text) == "The answer is 42"

    def test_preserves_pipe_tables(self, pp):
        text = "| Skill | Level |\n|---|---|\n| Python | Expert |"
        result = pp.clean_for_resume(text)
        assert "| Skill | Level |" in result
        assert "| Python | Expert |" in result

    def test_preserves_code_blocks(self, pp):
        text = "Some text\n```python\ndef hello():\n    pass\n```\nMore text"
        result = pp.clean_for_resume(text)
        assert "```python" in result
        assert "def hello():" in result

    def test_strips_bold_inside_text_preserving_tables(self, pp):
        text = "Use **Python** for this:\n| Lang | Level |\n|---|---|\n| **Python** | Expert |"
        result = pp.clean_for_resume(text)
        assert "Use Python for this:" in result
        assert "| **Python** | Expert |" in result

    def test_empty_input(self, pp):
        assert pp.clean_for_resume("") == ""
        assert pp.clean_for_resume(None) == ""

    def test_multiple_thinking_blocks(self, pp):
        text = "<think>first</think>\nmid<think>second</think>\nend"
        result = pp.clean_for_resume(text)
        assert "<think>" not in result
        assert result == "mid\nend"

    def test_strips_nested_html(self, pp):
        assert pp.clean_for_resume("<b><i>both</i></b>") == "both"


class TestCleanForJson:
    def test_removes_thinking_blocks(self, pp):
        text = "<think>hmm</think>\n{\"key\": \"value\"}"
        assert pp.clean_for_json(text) == '{"key": "value"}'

    def test_plain_json_passthrough(self, pp):
        text = '{"key": "value"}'
        assert pp.clean_for_json(text) == '{"key": "value"}'


class TestExtractJson:
    def test_valid_json(self, pp):
        assert pp.extract_json('{"a": 1}') == {"a": 1}

    def test_json_with_surrounding_text(self, pp):
        text = 'Here is the result: {"a": 1} done.'
        assert pp.extract_json(text) == {"a": 1}

    def test_json_with_thinking_blocks(self, pp):
        text = '<think>hmm</think>\n{"a": 1}'
        assert pp.extract_json(text) == {"a": 1}

    def test_invalid_json_returns_empty(self, pp):
        assert pp.extract_json("not json at all") == {}

    def test_nested_json(self, pp):
        text = '{"a": {"b": 2}}'
        assert pp.extract_json(text) == {"a": {"b": 2}}
