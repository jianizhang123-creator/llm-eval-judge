"""
Tests for the eval store — data persistence and stats calculation.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_store.store import load_data, save_data, DEFAULT_DATA
from eval_store.stats import update_stats


class TestStore:
    def test_load_returns_default_when_missing(self, tmp_path):
        fake_path = tmp_path / "nonexistent.json"
        with patch("eval_store.store.DATA_FILE", fake_path):
            data = load_data()
        assert data["samples"] == []
        assert data["knowledge_base"]["stats"]["total_evaluated"] == 0

    def test_save_and_load_round_trip(self, tmp_path):
        fake_path = tmp_path / "test.json"
        with patch("eval_store.store.DATA_FILE", fake_path):
            data = DEFAULT_DATA.copy()
            data["samples"] = [{"id": "test1"}]
            save_data(data)
            loaded = load_data()
        assert loaded["samples"][0]["id"] == "test1"


class TestStats:
    def _make_data(self, samples=None):
        data = json.loads(json.dumps(DEFAULT_DATA))
        if samples:
            data["samples"] = samples
        return data

    def test_correct_verdict(self):
        data = self._make_data()
        update_stats(data, {"overall_verdict": "correct"})
        assert data["knowledge_base"]["stats"]["total_evaluated"] == 1
        assert data["knowledge_base"]["stats"]["error_count"] == 0

    def test_error_verdict(self):
        data = self._make_data()
        update_stats(data, {"overall_verdict": "error"})
        assert data["knowledge_base"]["stats"]["error_count"] == 1

    def test_preference_verdict(self):
        data = self._make_data()
        update_stats(data, {"overall_verdict": "preference"})
        assert data["knowledge_base"]["stats"]["preference_count"] == 1

    def test_mixed_increments_both(self):
        data = self._make_data()
        update_stats(data, {"overall_verdict": "mixed"})
        assert data["knowledge_base"]["stats"]["error_count"] == 1
        assert data["knowledge_base"]["stats"]["preference_count"] == 1

    def test_accuracy_with_evaluated_samples(self):
        samples = [
            {
                "id": "s1",
                "eval_result": {
                    "classification": {
                        "modifications": [
                            {"field": "category", "type": "error"}
                        ]
                    }
                },
            },
            {
                "id": "s2",
                "eval_result": {"classification": None},  # correct
            },
        ]
        data = self._make_data(samples)
        update_stats(data, {"overall_verdict": "error"})
        acc = data["knowledge_base"]["stats"]["accuracy_by_field"]
        assert acc["category"] == 0.5   # 1 error out of 2
        assert acc["amount"] == 1.0     # no errors
