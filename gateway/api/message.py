"""WeCom Message Sending API Wrapper"""

import logging
import time

import requests

logger = logging.getLogger(__name__)


class WeComMessageAPI:
    """封装企微消息发送相关 API"""

    def __init__(self, token_manager, base_url="https://qyapi.weixin.qq.com"):
        self.token_manager = token_manager
        self.base_url = base_url

    def _request(self, method, path, **kwargs):
        """Send API request with token injection and retry."""
        token = self.token_manager.get_token()
        url = f"{self.base_url}{path}"
        params = kwargs.pop("params", {})
        params["access_token"] = token

        for attempt in range(3):
            try:
                resp = requests.request(method, url, params=params, timeout=10, **kwargs)
                resp.raise_for_status()
                data = resp.json()
                errcode = data.get("errcode", -1)
                if errcode == 0:
                    return data
                if errcode == 42001:
                    # Token expired, refresh and retry
                    logger.warning("Token expired on attempt %d, refreshing", attempt + 1)
                    self.token_manager._refresh()
                    params["access_token"] = self.token_manager.get_token()
                    continue
                return data  # Non-zero errcode, return as-is
            except requests.RequestException as e:
                logger.error("WeCom API request failed (attempt %d): %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return {"errcode": -1, "errmsg": "max retries exceeded"}

    def send_text(self, user_ids, content, agent_id=None):
        """
        Send text message to WeCom user(s).
        
        Args:
            user_ids: str (single user) or list of user IDs; use '@all' for everyone
            content: text content to send
            agent_id: override agent ID; defaults to token manager's agent
        
        Returns:
            dict: API response
        """
        if isinstance(user_ids, list):
            touser = "|".join(user_ids)
        else:
            touser = user_ids

        body = {
            "touser": touser,
            "msgtype": "text",
            "agentid": agent_id or 0,
            "text": {"content": content},
        }
        return self._request("POST", "/cgi-bin/message/send", json=body)

    def send_image(self, user_ids, media_id, agent_id=None):
        """Send image message using media_id."""
        if isinstance(user_ids, list):
            touser = "|".join(user_ids)
        else:
            touser = user_ids

        body = {
            "touser": touser,
            "msgtype": "image",
            "agentid": agent_id or 0,
            "image": {"media_id": media_id},
        }
        return self._request("POST", "/cgi-bin/message/send", json=body)

    def send_textcard(self, user_ids, title, description, url, agent_id=None):
        """Send a textcard (rich card) message."""
        if isinstance(user_ids, list):
            touser = "|".join(user_ids)
        else:
            touser = user_ids

        body = {
            "touser": touser,
            "msgtype": "textcard",
            "agentid": agent_id or 0,
            "textcard": {
                "title": title,
                "description": description,
                "url": url,
            },
        }
        return self._request("POST", "/cgi-bin/message/send", json=body)

    def send_news(self, user_ids, articles, agent_id=None):
        """Send news/MP article cards."""
        if isinstance(user_ids, list):
            touser = "|".join(user_ids)
        else:
            touser = user_ids

        body = {
            "touser": touser,
            "msgtype": "news",
            "agentid": agent_id or 0,
            "news": {"articles": articles},
        }
        return self._request("POST", "/cgi-bin/message/send", json=body)
