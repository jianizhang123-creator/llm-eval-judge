"""
Integration tests for the Flask API routes.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestDashboardRoutes:
    def test_presets_returns_samples(self, client, tmp_path):
        fake = tmp_path / "eval.json"
        fake.write_text('{"samples":[{"id":"s1"}],"knowledge_base":{"stats":{}}}')
        with patch("eval_store.store.DATA_FILE", fake):
            res = client.get("/api/presets")
        assert res.status_code == 200
        assert res.get_json()["samples"][0]["id"] == "s1"

    def test_dashboard_returns_stats(self, client, tmp_path):
        fake = tmp_path / "eval.json"
        fake.write_text('{"samples":[],"knowledge_base":{"stats":{"total_evaluated":5}}}')
        with patch("eval_store.store.DATA_FILE", fake):
            res = client.get("/api/dashboard")
        assert res.get_json()["total_evaluated"] == 5

    def test_knowledge_returns_kb(self, client, tmp_path):
        fake = tmp_path / "eval.json"
        fake.write_text('{"samples":[],"knowledge_base":{"errors":[],"patterns":[],"stats":{}}}')
        with patch("eval_store.store.DATA_FILE", fake):
            res = client.get("/api/knowledge")
        assert "errors" in res.get_json()
