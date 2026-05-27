"""WeCom API Authentication & Access Token Management"""

import hashlib
import hmac
import json
import logging
import time

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

logger = logging.getLogger(__name__)


def verify_signature(token, msg_signature, timestamp, nonce, echostr=None):
    """
    Verify WeCom callback signature.
    
    WeCom callback signature algorithm:
    1. Sort [token, timestamp, nonce, encrypt_msg] alphabetically
    2. Concat and SHA1 hash
    3. Compare with msg_signature
    
    Args:
        token: WeCom callback token
        msg_signature: signature from WeCom
        timestamp: request timestamp
        nonce: random nonce
        echostr: encrypted echo string (for URL verification)
    
    Returns:
        bool: whether signature is valid
    """
    params = sorted([token, timestamp, nonce])
    if echostr:
        params.append(echostr)
    combined = "".join(params)
    computed = hashlib.sha1(combined.encode("utf-8")).hexdigest()
    return computed == msg_signature


def verify_callback_body(token, msg_signature, timestamp, nonce, body):
    """
    Verify signature for POST callback body.
    Extracts the msg_encrypt field from the body.
    """
    try:
        body_obj = json.loads(body) if isinstance(body, str) else body
        msg_encrypt = body_obj.get("encrypt", "")
    except (json.JSONDecodeError, AttributeError):
        return False
    return verify_signature(token, msg_signature, timestamp, nonce, msg_encrypt)


def decrypt_echostr(encoding_aes_key_b64, corp_id, encrypted_text):
    """
    Decrypt WeCom echostr during URL verification.
    
    Returns the decoded echostr string.
    """
    import base64
    
    aes_key = base64.b64decode(encoding_aes_key_b64 + "=")
    cipher_text = base64.b64decode(encrypted_text)
    
    iv = aes_key[:16]
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(cipher_text) + decryptor.finalize()
    
    # Remove PKCS#7 padding
    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted) + unpadder.finalize()
    
    # Format: 16 random bytes + 4-byte msg len + msg content + corp_id
    content = decrypted[16:]
    msg_len = int.from_bytes(content[:4], byteorder="big")
    msg = content[4: 4 + msg_len].decode("utf-8")
    recv_corp_id = content[4 + msg_len:].decode("utf-8")
    
    if recv_corp_id != corp_id:
        raise ValueError(f"Corp ID mismatch: expected {corp_id}, got {recv_corp_id}")
    
    return msg


class AccessTokenManager:
    """
    Manages WeCom access_token with caching and automatic refresh.
    
    WeCom access_token expires every 7200 seconds. This class caches
    the token and refreshes it before expiry.
    """

    def __init__(self, corp_id, corp_secret, base_url="https://qyapi.weixin.qq.com"):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.base_url = base_url
        self._token = None
        self._expires_at = 0
        self._lock = False

    def get_token(self, refresh_before=300):
        """
        Get a valid access_token, refreshing if needed.
        
        Args:
            refresh_before: refresh this many seconds before expiry
        
        Returns:
            str: valid access_token
        """
        now = time.time()
        if self._token is None or now >= (self._expires_at - refresh_before):
            self._refresh()
        return self._token

    def _refresh(self):
        """Fetch a new access_token from WeCom API."""
        url = f"{self.base_url}/cgi-bin/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.corp_secret,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errcode", 0) != 0:
                raise ValueError(
                    f"WeCom API error: errcode={data.get('errcode')}, "
                    f"errmsg={data.get('errmsg')}"
                )
            self._token = data["access_token"]
            self._expires_at = time.time() + data.get("expires_in", 7200)
            logger.info(
                "WeCom access_token refreshed, expires in %ds",
                data.get("expires_in", 7200),
            )
        except requests.RequestException as e:
            logger.error("Failed to refresh WeCom access_token: %s", e)
            if self._token is None:
                raise
            # Use stale token as fallback
            logger.warning("Using stale access_token as fallback")
