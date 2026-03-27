"""
Read-only JSON endpoints: presets, dashboard stats, and knowledge base.
"""

from flask import Blueprint

from eval_store.store import load_data

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/api/presets")
def api_presets():
    data = load_data()
    return {"samples": data.get("samples", [])}


@dashboard_bp.route("/api/dashboard")
def api_dashboard():
    data = load_data()
    return data.get("knowledge_base", {}).get("stats", {})


@dashboard_bp.route("/api/knowledge")
def api_knowledge():
    data = load_data()
    return data.get("knowledge_base", {})
