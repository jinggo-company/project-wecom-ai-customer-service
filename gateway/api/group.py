"""WeCom Group (群管理) API Wrapper"""

import logging
import time

import requests

logger = logging.getLogger(__name__)


class WeComGroupAPI:
    """封装企微群管理 API"""

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
                resp = requests.request(method, url, params=params, timeout=10, **kwargs)
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
                logger.error("WeCom Group API failed (attempt %d): %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return {"errcode": -1, "errmsg": "max retries exceeded"}

    def create_group_chat(self, name, owner_userid, userlist=None, chatid=None):
        """
        Create a group chat.
        
        Args:
            name: group name
            owner_userid: group owner userid
            userlist: list of member userids
            chatid: optional custom chat id
        
        Returns:
            dict: API response with chatid
        """
        body = {"name": name, "owner": owner_userid}
        if userlist:
            body["userlist"] = userlist
        if chatid:
            body["chatid"] = chatid
        return self._request("POST", "/cgi-bin/appchat/create", json=body)

    def get_group_chat(self, chat_id):
        """Get group chat details."""
        return self._request(
            "GET", "/cgi-bin/appchat/get", params={"chatid": chat_id}
        )

    def update_group_chat(self, chat_id, name=None, owner=None, add_userlist=None, del_userlist=None):
        """Update group chat settings."""
        body = {"chatid": chat_id}
        if name:
            body["name"] = name
        if owner:
            body["owner"] = owner
        if add_userlist:
            body["add_user_list"] = add_userlist
        if del_userlist:
            body["del_user_list"] = del_userlist
        return self._request("POST", "/cgi-bin/appchat/update", json=body)

    def send_group_message(self, chat_id, msgtype, content):
        """
        Send a message to a group chat.
        
        Args:
            chat_id: group chat ID
            msgtype: message type (text/image/news/markdown)
            content: message content dict
        
        Returns:
            dict: API response
        """
        body = {"chatid": chat_id, "msgtype": msgtype, msgtype: content}
        return self._request("POST", "/cgi-bin/appchat/send", json=body)
