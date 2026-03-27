"""
LLM Eval Judge Server
Flask application factory — registers route blueprints and serves the
single-page frontend.
"""

from flask import Flask, send_from_directory

from config import BASE_DIR
from routes import evaluate_bp, batch_bp, analyze_bp, dashboard_bp

app = Flask(__name__, static_folder=str(BASE_DIR / "static"))

app.register_blueprint(evaluate_bp)
app.register_blueprint(batch_bp)
app.register_blueprint(analyze_bp)
app.register_blueprint(dashboard_bp)


@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR / "static"), "index.html")


if __name__ == "__main__":
    print(f"[LLM Eval Judge] starting on http://127.0.0.1:8080")
    app.run(host="127.0.0.1", port=8080, debug=True)
