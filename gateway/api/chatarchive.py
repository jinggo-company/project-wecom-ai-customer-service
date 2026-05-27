"""WeCom Chat Archive (会话存档) API Wrapper"""

import logging
import time

import requests

logger = logging.getLogger(__name__)


class WeComChatArchiveAPI:
    """
    企微会话存档 API 封装.
    会话存档是付费功能，需单独购买并配置 RSA 私钥.
    """

    def __init__(self, token_manager, base_url="https://qyapi.weixin.qq.com"):
        self.token_manager = token_manager
        self.base_url = base_url

    def _request(self, method, path, **kwargs):
        token = self.token_manager.get_token()
        url = f"{self.base_url}{path}"
        params = kwargs.pop("params", {})
        params["access_token"] = token

        for attempt in range(3):
            try:
                resp = requests.request(method, url, params=params, timeout=30, **kwargs)
                resp.raise_for_status()
                data = resp.json()
                errcode = data.get("errcode", -1)
                if errcode == 0:
                    return data
                if errcode == 42001:
                    self.token_manager._refresh()
                    params["access_token"] = self.token_manager.get_token()
                    continue
                return data
            except requests.RequestException as e:
                logger.error("WeCom ChatArchive API failed (attempt %d): %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return {"errcode": -1, "errmsg": "max retries exceeded"}

    def get_media_data(self, sdkfileid, proxy_url=None):
        """
        Download media file from chat archive.
        
        Args:
            sdkfileid: media file SDK file ID
            proxy_url: optional proxy URL for download
        
        Returns:
            bytes: media file content
        """
        token = self.token_manager.get_token()
        url = f"{self.base_url}/cgi-bin/media/get"
        params = {
            "access_token": token,
            "sdkfileid": sdkfileid,
        }
        resp = requests.get(url, params=params, timeout=60, stream=True)
        resp.raise_for_status()
        return resp.content

    def get_chat_data(self, seq, limit=1000, userid=None):
        """
        Pull chat archive data (incremental).
        
        Args:
            seq: sequence number for incremental pull (0 for first pull)
            limit: max records per pull (max 1000)
            userid: optional filter by specific user
        
        Returns:
            dict: API response with chat_data list and next seq
        """
        body = {
            "seq": seq,
            "limit": limit,
        }
        if userid:
            body["userid"] = userid

        return self._request("POST", "/cgi-bin/externalcontact/get_corp_chat_list", json=body)
