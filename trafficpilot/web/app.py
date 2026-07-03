"""Flask application exposing the TrafficPilot AI dashboard.

Run with::

    python -m trafficpilot.web.app          # or: flask --app trafficpilot.web.app run

Routes
------
GET  /                     -> the dashboard (server-rendered shell + JS)
GET  /api/dashboard        -> full analytics payload (JSON)
GET  /api/recommendations  -> recommendations only (JSON)
GET  /api/health           -> liveness probe
"""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from trafficpilot.service import TrafficPilotService


def create_app() -> Flask:
    app = Flask(__name__)

    # Build the service once at startup (loads artifacts or trains on demand).
    service = TrafficPilotService(auto_train=True)
    app.config["SERVICE"] = service

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/api/dashboard")
    def api_dashboard():
        return jsonify(app.config["SERVICE"].dashboard())

    @app.route("/api/recommendations")
    def api_recommendations():
        return jsonify(app.config["SERVICE"].recommendations())

    @app.route("/api/audit")
    def api_audit():
        url = (request.args.get("url") or "").strip()
        if not url:
            return jsonify({"ok": False, "error": "Provide a ?url= parameter."}), 400
        country = (request.args.get("country") or "").strip() or None
        return jsonify(app.config["SERVICE"].audit(url, target_country=country))

    @app.route("/api/health")
    def api_health():
        return jsonify({"status": "ok"})

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=5000, debug=False)
