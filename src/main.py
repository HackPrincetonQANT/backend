from __future__ import annotations

import logging
from typing import Dict

from flask import Flask, jsonify, request
from flask_cors import CORS


def create_app() -> Flask:
    """Application factory that configures routes, CORS, and logging."""
    app = Flask(__name__)
    CORS(app)

    configure_logging(app)
    register_routes(app)

    @app.before_request
    def log_request() -> None:
        app.logger.info("%s %s", request.method, request.path)

    return app


def configure_logging(app: Flask) -> None:
    """Set up a basic stream handler if none exist."""
    if app.logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def register_routes(app: Flask) -> None:
    @app.post("/events/transaction")
    def transaction_event() -> tuple[Dict[str, str], int]:
        return jsonify({"transaction_id": "mock123"}), 200

    @app.post("/notifications/reply")
    def notifications_reply() -> tuple[Dict[str, bool], int]:
        return jsonify({"ok": True}), 200

    @app.get("/user/<user_id>/summary")
    def user_summary(user_id: str) -> tuple[Dict[str, object], int]:
        data: Dict[str, object] = {"recent": [], "predictions": {}}
        return jsonify(data), 200


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
