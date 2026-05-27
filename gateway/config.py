"""WeCom Gateway Configuration"""

import os


class Config:
    """Gateway service configuration."""

    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
    HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT = int(os.getenv("FLASK_PORT", "5000"))

    # WeCom Corporation settings
    WECOM_CORP_ID = os.getenv("WECOM_CORP_ID", "")
    WECOM_AGENT_ID = os.getenv("WECOM_AGENT_ID", "")
    WECOM_AGENT_SECRET = os.getenv("WECOM_AGENT_SECRET", "")

    # WeCom webhook callback verification
    WECOM_TOKEN = os.getenv("WECOM_TOKEN", "")
    WECOM_ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY", "")

    # WeCom session archive (会话存档)
    WECOM_CHATARCHIVE_SECRET = os.getenv("WECOM_CHATARCHIVE_SECRET", "")

    # Callback URL that WeCom will POST to
    CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL", "http://localhost:5000")

    # Redis for token caching and idempotency
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Access token TTL (WeCom tokens expire every 7200s; refresh at 7000s)
    ACCESS_TOKEN_REFRESH_BEFORE = int(
        os.getenv("ACCESS_TOKEN_REFRESH_BEFORE", "300")
    )

    # Retry settings for WeCom API calls
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_BASE = float(os.getenv("RETRY_BACKOFF_BASE", "2.0"))
    RETRY_INITIAL_DELAY = float(os.getenv("RETRY_INITIAL_DELAY", "1.0"))

    # Message idempotency window (seconds)
    IDEMPOTENCY_WINDOW = int(os.getenv("IDEMPOTENCY_WINDOW", "300"))

    # AI engine endpoint (where to forward messages for AI processing)
    AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://localhost:8000/api/agent/reply")
    AI_ENGINE_TIMEOUT = int(os.getenv("AI_ENGINE_TIMEOUT", "30"))
