"""WeCom Media File Callback Handler"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

# Default storage path for downloaded media
MEDIA_STORAGE_PATH = os.getenv("MEDIA_STORAGE_PATH", "/tmp/wecom_media")


def get_media(token_manager, media_id, media_type="image"):
    """
    Download media file from WeCom.
    
    Args:
        token_manager: AccessTokenManager instance
        media_id: WeCom media ID
        media_type: image/voice/video/file
    
    Returns:
        tuple: (file_path_or_url, file_size) or (None, error_msg)
    """
    token = token_manager.get_token()
    url = "https://qyapi.weixin.qq.com/cgi-bin/media/get"
    params = {"access_token": token, "media_id": media_id}

    try:
        resp = requests.get(url, params=params, timeout=30, stream=True)
        resp.raise_for_status()

        # Check if response is JSON (error)
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            error_data = resp.json()
            return None, error_data.get("errmsg", "unknown error")

        # Save to local storage
        os.makedirs(MEDIA_STORAGE_PATH, exist_ok=True)
        ext = _get_extension(media_type)
        file_path = os.path.join(MEDIA_STORAGE_PATH, f"{media_id}{ext}")

        with open(file_path, "wb") as f:
            total = 0
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                total += len(chunk)

        logger.info("Media downloaded: %s (%d bytes)", file_path, total)
        return file_path, total

    except requests.RequestException as e:
        logger.error("Failed to download media %s: %s", media_id, e)
        return None, str(e)


def get_media_url(token_manager, media_id, media_type="image"):
    """
    Get a direct download URL for media (without downloading).
    
    Returns:
        str: download URL with token
    """
    token = token_manager.get_token()
    return (
        f"https://qyapi.weixin.qq.com/cgi-bin/media/get"
        f"?access_token={token}&media_id={media_id}"
    )


def _get_extension(media_type):
    """Map media type to file extension."""
    extensions = {
        "image": ".jpg",
        "voice": ".amr",
        "video": ".mp4",
        "file": ".bin",
    }
    return extensions.get(media_type, ".bin")
