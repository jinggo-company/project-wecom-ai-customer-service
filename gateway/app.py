"""WeCom AI Customer Service — Gateway Flask Application"""

import logging
from logging.handlers import RotatingFileHandler
import os

from flask import Flask, jsonify

from gateway.config import Config
from gateway.webhook.message import webhook_bp


def create_app(config_class=None):
    """
    Flask application factory.
    
    Creates and configures the Flask app with all blueprints.
    """
    app = Flask(__name__)
    
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(webhook_bp, url_prefix="/webhook")

    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy", "service": "wecom-gateway"})

    # URL verification endpoint (WeCom GET request)
    @app.route("/webhook/verify", methods=["GET"])
    def verify_callback():
        """
        WeCom URL verification endpoint.
        
        WeCom sends a GET request with msg_signature, timestamp, nonce, echostr
        to verify the callback URL.
        """
        from flask import request
        from gateway.api.auth import verify_signature, decrypt_echostr
        
        msg_signature = request.args.get("msg_signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")

        token = app.config.get("WECOM_TOKEN", "")
        encoding_aes_key = app.config.get("WECOM_ENCODING_AES_KEY", "")
        corp_id = app.config.get("WECOM_CORP_ID", "")

        # Verify signature (skip in dev mode when no token configured)
        if token and not verify_signature(token, msg_signature, timestamp, nonce, echostr):
            return "signature verification failed", 403

        # Decrypt echostr and return the plain text
        try:
            if encoding_aes_key:
                decrypted = decrypt_echostr(encoding_aes_key, corp_id, echostr)
                return decrypted
            return echostr  # Non-encrypted mode
        except Exception as e:
            logging.error("Failed to decrypt echostr: %s", e)
            return "decryption failed", 500

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "internal server error"}), 500

    # Configure logging
    setup_logging(app)

    return app


def setup_logging(app):
    """Configure application logging."""
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO"))
    
    # File handler with rotation
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "gateway.log")
    
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)


if __name__ == "__main__":
    app = create_app()
    app.run(host=Config.HOST, port=Config.PORT, debug=True)
