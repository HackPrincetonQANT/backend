from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()  
import logging
import logging
import os  # Added for environment variables
import base64  # Added for Basic Auth
import requests  # Added for making API calls
import hmac  # Added for webhook verification
import hashlib  # Added for webhook verification
from typing import Dict

from flask import Flask, jsonify, request
from flask_cors import CORS


def create_app() -> Flask:
    """Application factory that configures routes, CORS, and logging."""
    app = Flask(__name__)
    CORS(app)

    configure_logging(app)
    register_routes(app)
    register_knot_routes(app)  # Register the new Knot routes

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

# --- NEW KNOT INTEGRATION ---
# This section replicates the logic from your friend's project.

def register_knot_routes(app: Flask) -> None:
    """
    Registers all the Knot API routes for session creation and webhooks.
    """

    @app.post("/api/knot/create-session")
    def create_knot_session():
        """
        Securely creates a Knot session from the backend.
        This replicates: src/app/api/knot/create-session/route.ts
        """
        try:
            # 1. Get client credentials from environment
            client_id = os.environ.get("KNOT_CLIENT_ID")
            api_secret = os.environ.get("KNOT_API_SECRET")

            if not client_id or not api_secret:
                return jsonify({"error": "Knot credentials not configured"}), 500

            # 2. Get data from your frontend's request
            data = request.get_json()
            user_id = data.get("userId")
            product = data.get("product", "transaction_link") # Default to transaction_link

            if not user_id:
                return jsonify({"error": "Missing userId"}), 400

            # 3. Create Basic Auth token (like in your friend's 'create-session' route)
            #
            auth_string = f"{client_id}:{api_secret}"
            encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
            
            # 4. Define the Knot API endpoint and payload
            #
            knot_api_url = "https://development.knotapi.com/session/create"
            payload = {
                "external_user_id": user_id,
                "type": product
            }
            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Knot-Version": "2.0" #
            }

            # 5. Make the secure request to Knot
            response = requests.post(knot_api_url, json=payload, headers=headers)
            response.raise_for_status()

            # 6. Get the response JSON
            response_data = response.json()

            # 7. Standardize the response to match the frontend's expectation
            #    This matches the logic in DealyDigest
            if "session" in response_data and "session_id" not in response_data:
                response_data["session_id"] = response_data["session"]

            # 8. Return the standardized data to your frontend
            return jsonify(response_data), response.status_code

        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error creating Knot session: {e}")
            if e.response is not None:
                return jsonify({"error": "Failed to create Knot session", "details": e.response.text}), e.response.status_code
            return jsonify({"error": "Failed to create Knot session", "details": str(e)}), 500
        except Exception as e:
            app.logger.error(f"Unexpected error in create_knot_session: {e}")
            return jsonify({"error": "Internal server error"}), 500

    @app.post("/api/knot/webhooks")
    def knot_webhooks():
        """
        Receives and verifies webhooks from Knot.
        This replicates: src/app/api/knot/webhooks/route.ts
        And verification logic from: src/lib/knot.ts
        """
        data = request.get_json()
        app.logger.info(f"Received Knot Webhook: {data.get('event')}")

        # --- Webhook Signature Verification ---
        # This logic is translated from src/lib/knot.ts [verifyWebhookSignature]
        try:
            api_secret = os.environ.get("KNOT_API_SECRET")
            if not api_secret:
                app.logger.error("KNOT_API_SECRET not set, cannot verify webhook")
                return jsonify({"error": "Webhook configuration error"}), 500

            signature = request.headers.get("knot-signature")
            if not signature:
                return jsonify({"error": "Missing signature"}), 401

            # 1. Build the data map
            data_map = {
                "Content-Length": request.headers.get("Content-Length", ""),
                "Content-Type": request.headers.get("Content-Type", ""),
                "Encryption-Type": request.headers.get("Encryption-Type", ""),
                "event": data.get("event", "")
            }
            if data.get("session_id"):
                 data_map["session_id"] = data.get("session_id")

            # 2. Build the signature string
            signature_string = "|".join([f"{k}|{v}" for k, v in data_map.items()])

            # 3. Compute the HMAC-SHA256 signature
            digest = hmac.new(
                api_secret.encode('utf-8'),
                signature_string.encode('utf-8'),
                hashlib.sha256
            ).digest()
            computed_signature = base64.b64encode(digest).decode('utf-8')

            # 4. Compare signatures securely
            if not hmac.compare_digest(computed_signature, signature):
                app.logger.warning("Invalid Knot webhook signature")
                return jsonify({"error": "Invalid signature"}), 401

            app.logger.info(f"Webhook signature verified for event: {data.get('event')}")

        except Exception as e:
            app.logger.error(f"Error verifying webhook signature: {e}")
            return jsonify({"error": "Signature verification failed"}), 500

        # --- Process the Webhook ---
        # Now that it's verified, you can process it (e.g., save to DB, etc.)
        # Your friend's project calls `processWebhook` here
        # For now, we'll just log it.
        
        event_type = data.get('event')
        if event_type == "TRANSACTION_SYNC_COMPLETE":
            app.logger.info("Transaction sync complete! Ready to fetch data.")

        
        return jsonify({"success": True}), 200



app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)