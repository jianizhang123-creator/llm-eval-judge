"""
Tests for agent utilities — JSON parsing and prompt loading.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.base import parse_json_response, load_prompt


class TestParseJsonResponse:
    def test_direct_json(self):
        raw = json.dumps({"key": "value"})
        assert parse_json_response(raw) == {"key": "value"}

    def test_markdown_fence(self):
        raw = "Some text\n```json\n{\"a\": 1}\n```\nmore text"
        assert parse_json_response(raw) == {"a": 1}

    def test_brace_extraction(self):
        raw = 'Here is the result: {"b": 2} — done.'
        assert parse_json_response(raw) == {"b": 2}

    def test_trailing_comma_cleanup(self):
        raw = '{"a": 1, "b": 2,}'
        result = parse_json_response(raw)
        assert result == {"a": 1, "b": 2}

    def test_unparseable_returns_none(self):
        assert parse_json_response("not json at all") is None


class TestLoadPrompt:
    def test_loads_classification_prompt(self):
        prompt = load_prompt("classification")
        assert "quality judge" in prompt.lower()

    def test_loads_annotation_prompt(self):
        prompt = load_prompt("annotation")
        assert "error annotation" in prompt.lower()

    def test_missing_prompt_raises(self):
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_agent")
