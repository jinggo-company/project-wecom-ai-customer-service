"""WeCom Contact (通讯录) API Wrapper"""

import logging
import time

import requests

logger = logging.getLogger(__name__)


class WeComContactAPI:
    """封装企微通讯录管理 API"""

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
                    self.token_manager._refresh()
                    params["access_token"] = self.token_manager.get_token()
                    continue
                return data
            except requests.RequestException as e:
                logger.error("WeCom Contact API failed (attempt %d): %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return {"errcode": -1, "errmsg": "max retries exceeded"}

    def list_departments(self, department_id=None):
        """List departments. If department_id is given, list sub-departments."""
        params = {}
        if department_id:
            params["id"] = department_id
        return self._request("GET", "/cgi-bin/department/list", params=params)

    def list_users(self, department_id, fetch_child=False):
        """List users in a department."""
        params = {"department_id": department_id, "fetch_child": 1 if fetch_child else 0}
        return self._request("GET", "/cgi-bin/user/list", params=params)

    def get_user(self, userid):
        """Get user detail by userid."""
        return self._request("GET", "/cgi-bin/user/get", params={"userid": userid})

    def get_external_contact(self, userid, external_userid):
        """Get external contact detail."""
        return self._request(
            "GET",
            "/cgi-bin/externalcontact/get",
            params={"userid": userid, "external_userid": external_userid},
        )

    def list_external_contacts(self, userid):
        """List external contacts for a staff member."""
        return self._request(
            "GET", "/cgi-bin/externalcontact/list", params={"userid": userid}
        )
