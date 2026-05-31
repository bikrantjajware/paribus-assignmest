from __future__ import annotations
import os
from dotenv import load_dotenv
load_dotenv()
import logging

from flask import Flask, jsonify
from app.extensions import hospital_api_client

from app.routes import hospitals_bp


logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    app.register_blueprint(hospitals_bp)
    app.config["HOSPITAL_API_BASE_URL"] = os.getenv("HOSPITAL_API_BASE_URL")
    hospital_api_client.init_app(app)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    logger.info("Application initialised; blueprints: %s", [hospitals_bp.name])
    return app


app = create_app()