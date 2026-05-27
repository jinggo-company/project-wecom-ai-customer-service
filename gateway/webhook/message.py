"""WeCom Message Callback Handler"""

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

webhook_bp = Blueprint("webhook", __name__)

# In-memory processed message cache (production: use Redis)
_processed_messages = {}


def is_message_duplicate(msg_id, window=300):
    """
    Check if a message has been processed within the idempotency window.
    
    Args:
        msg_id: unique message identifier
        window: dedup window in seconds
    
    Returns:
        bool: True if message is a duplicate
    """
    now = time.time()
    if msg_id in _processed_messages:
        if now - _processed_messages[msg_id] < window:
            return True
    _processed_messages[msg_id] = now
    # Clean expired entries
    expired = [k for k, v in _processed_messages.items() if now - v >= window]
    for k in expired:
        del _processed_messages[k]
    return False


def parse_message_content(msg_data):
    """
    Parse WeCom callback message into a standardized format.
    
    Args:
        msg_data: raw message dict from WeCom callback
    
    Returns:
        dict: standardized message with fields:
            - msgid: unique message ID
            - from_user: sender external user ID
            - to_user: receiver staff user ID
            - msg_type: text/image/voice/file/link/etc
            - content: message content (str or dict)
            - timestamp: message timestamp (datetime)
            - raw: original WeCom message dict
    """
    msg_type = msg_data.get("MsgType", "")
    from_user = msg_data.get("FromUserName", "")
    to_user = msg_data.get("ToUserName", "")
    msg_id = msg_data.get("MsgId", "")
    timestamp = msg_data.get("CreateTime", 0)

    content = {}
    if msg_type == "text":
        content = msg_data.get("Content", "")
    elif msg_type == "image":
        content = {
            "media_id": msg_data.get("MediaId", ""),
            "pic_url": msg_data.get("PicUrl", ""),
        }
    elif msg_type == "voice":
        content = {
            "media_id": msg_data.get("MediaId", ""),
            "format": msg_data.get("Format", ""),
        }
    elif msg_type == "video":
        content = {
            "media_id": msg_data.get("MediaId", ""),
            "thumb_media_id": msg_data.get("ThumbMediaId", ""),
        }
    elif msg_type == "file":
        content = {
            "media_id": msg_data.get("MediaId", ""),
            "file_name": msg_data.get("FileName", ""),
            "file_size": msg_data.get("FileSize", ""),
        }
    elif msg_type == "link":
        content = {
            "title": msg_data.get("Title", ""),
            "description": msg_data.get("Description", ""),
            "url": msg_data.get("Url", ""),
        }
    elif msg_type == "location":
        content = {
            "location_x": msg_data.get("Location_X", ""),
            "location_y": msg_data.get("Location_Y", ""),
            "scale": msg_data.get("Scale", ""),
            "label": msg_data.get("Label", ""),
        }

    return {
        "msgid": msg_id,
        "from_user": from_user,
        "to_user": to_user,
        "msg_type": msg_type,
        "content": content,
        "timestamp": datetime.fromtimestamp(int(timestamp), tz=timezone.utc) if timestamp else None,
        "raw": msg_data,
    }


def get_message_id_for_dedup(msg_data):
    """
    Extract or generate a unique message ID for deduplication.
    
    WeCom provides MsgId for messages. For events, we use a composite key.
    """
    msg_id = msg_data.get("MsgId", "")
    if msg_id:
        return str(msg_id)
    
    # For events without MsgId, create composite key
    from_user = msg_data.get("FromUserName", "")
    timestamp = msg_data.get("CreateTime", "0")
    event = msg_data.get("Event", "")
    composite = f"event:{from_user}:{timestamp}:{event}"
    return hashlib.md5(composite.encode()).hexdigest()


@webhook_bp.route("/callback", methods=["POST"])
def handle_callback():
    """
    Handle WeCom message/event callback.
    
    Receives encrypted or plaintext POST from WeCom server,
    parses the message, checks idempotency, and routes accordingly.
    """
    from gateway.config import Config

    # Get signature params from query string
    msg_signature = request.args.get("msg_signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    # Verify signature if configured
    if Config.WECOM_TOKEN:
        from gateway.api.auth import verify_callback_body

        if not verify_callback_body(
            Config.WECOM_TOKEN, msg_signature, timestamp, nonce, request.data
        ):
            logger.warning("Invalid callback signature from WeCom")
            return jsonify({"error": "invalid signature"}), 401

    # Parse message
    try:
        # Handle encrypted XML body if encoding is enabled
        if Config.WECOM_ENCODING_AES_KEY:
            # In production, decrypt the encrypted XML here
            # For now, parse as JSON (WeCom can send JSON callbacks)
            msg_data = request.get_json(force=True)
        else:
            msg_data = request.get_json(force=True)
    except Exception as e:
        logger.error("Failed to parse callback body: %s", e)
        return jsonify({"error": "bad request body"}), 400

    if not msg_data:
        logger.warning("Empty callback body")
        return jsonify({"error": "empty body"}), 400

    # Idempotency check
    dedup_key = get_message_id_for_dedup(msg_data)
    if is_message_duplicate(dedup_key, window=Config.IDEMPOTENCY_WINDOW):
        logger.info("Duplicate message skipped: %s", dedup_key)
        return "success"  # Return success to avoid WeCom retry

    # Parse standardized message
    msg = parse_message_content(msg_data)
    logger.info(
        "Received message: type=%s, from=%s, to=%s, msgid=%s",
        msg["msg_type"], msg["from_user"], msg["to_user"], msg["msgid"],
    )

    # Route message based on type
    msg_type = msg_data.get("MsgType", "")
    event = msg_data.get("Event", "")

    if msg_type == "event":
        # Delegate to event handler
        from gateway.webhook.event import handle_event_message

        result = handle_event_message(msg_data)
    else:
        # Normal message — forward to AI engine or process
        result = {"status": "received", "msgid": msg["msgid"], "routed": "pending"}
        logger.info(
            "Message queued for processing: msgid=%s, type=%s",
            msg["msgid"], msg_type,
        )

    # Return success to WeCom (must respond within 5 seconds)
    return "success"
