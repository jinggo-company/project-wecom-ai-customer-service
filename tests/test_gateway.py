"""WeCom AI Customer Service — Gateway Tests"""

import json
import time
import unittest
from unittest.mock import MagicMock, patch

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestAuthSignature(unittest.TestCase):
    """Test auth.py signature verification and token management."""

    def test_verify_signature_valid(self):
        """Test valid signature verification."""
        from gateway.api.auth import verify_signature

        # Manually compute a valid signature
        import hashlib
        token = "test_token"
        timestamp = "1234567890"
        nonce = "abcdef"
        params = sorted([token, timestamp, nonce])
        combined = "".join(params)
        expected_sig = hashlib.sha1(combined.encode("utf-8")).hexdigest()

        result = verify_signature(token, expected_sig, timestamp, nonce)
        self.assertTrue(result)

    def test_verify_signature_invalid(self):
        """Test invalid signature rejection."""
        from gateway.api.auth import verify_signature

        result = verify_signature("token", "bad_signature", "123", "nonce")
        self.assertFalse(result)

    def test_verify_signature_with_echostr(self):
        """Test signature verification including echostr."""
        from gateway.api.auth import verify_signature
        import hashlib

        token = "my_token"
        timestamp = "1700000000"
        nonce = "xyz"
        echostr = "encrypted_string"
        # verify_signature sorts [token, timestamp, nonce] then appends echostr
        params = sorted([token, timestamp, nonce])
        params.append(echostr)
        combined = "".join(params)
        sig = hashlib.sha1(combined.encode("utf-8")).hexdigest()

        result = verify_signature(token, sig, timestamp, nonce, echostr)
        self.assertTrue(result)

    @patch("gateway.api.auth.requests.get")
    def test_access_token_manager_refresh(self, mock_get):
        """Test access token refresh."""
        from gateway.api.auth import AccessTokenManager

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "errcode": 0,
            "errmsg": "ok",
            "access_token": "test_token_123",
            "expires_in": 7200,
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        mgr = AccessTokenManager("corp_id", "corp_secret")
        token = mgr.get_token()

        self.assertEqual(token, "test_token_123")
        mock_get.assert_called_once()

    @patch("gateway.api.auth.requests.get")
    def test_access_token_uses_cached(self, mock_get):
        """Test that cached token is returned without API call."""
        from gateway.api.auth import AccessTokenManager

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "errcode": 0,
            "errmsg": "ok",
            "access_token": "cached_token",
            "expires_in": 7200,
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        mgr = AccessTokenManager("corp_id", "corp_secret")
        token1 = mgr.get_token()
        token2 = mgr.get_token()  # Should use cache

        self.assertEqual(token1, token2)
        mock_get.assert_called_once()  # Only one API call

    @patch("gateway.api.auth.requests.get")
    def test_access_token_refresh_on_expiry(self, mock_get):
        """Test token refresh after expiry."""
        from gateway.api.auth import AccessTokenManager

        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            mock_resp = MagicMock()
            if call_count["n"] == 1:
                mock_resp.json.return_value = {
                    "errcode": 0,
                    "errmsg": "ok",
                    "access_token": "token_v1",
                    "expires_in": 1,  # Expires in 1 second
                }
            else:
                mock_resp.json.return_value = {
                    "errcode": 0,
                    "errmsg": "ok",
                    "access_token": "token_v2",
                    "expires_in": 7200,
                }
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        mock_get.side_effect = side_effect

        mgr = AccessTokenManager("corp_id", "corp_secret")
        token1 = mgr.get_token()
        
        # Simulate time passing
        mgr._expires_at = time.time() - 100  # Already expired
        
        token2 = mgr.get_token()

        self.assertEqual(token1, "token_v1")
        self.assertEqual(token2, "token_v2")
        self.assertEqual(mock_get.call_count, 2)


class TestMessageAPI(unittest.TestCase):
    """Test api/message.py WeComMessageAPI."""

    def setUp(self):
        self.mock_token_mgr = MagicMock()
        self.mock_token_mgr.get_token.return_value = "test_token"

    @patch("gateway.api.message.requests.request")
    def test_send_text(self, mock_req):
        """Test sending text message."""
        from gateway.api.message import WeComMessageAPI

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_resp.raise_for_status.return_value = None
        mock_req.return_value = mock_resp

        api = WeComMessageAPI(self.mock_token_mgr)
        result = api.send_text("user1", "Hello, World!")

        self.assertEqual(result["errcode"], 0)
        mock_req.assert_called_once()
        call_kwargs = mock_req.call_args
        self.assertEqual(call_kwargs[1]["json"]["touser"], "user1")
        self.assertEqual(call_kwargs[1]["json"]["text"]["content"], "Hello, World!")

    @patch("gateway.api.message.requests.request")
    def test_send_text_to_multiple(self, mock_req):
        """Test sending text to multiple users."""
        from gateway.api.message import WeComMessageAPI

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_resp.raise_for_status.return_value = None
        mock_req.return_value = mock_resp

        api = WeComMessageAPI(self.mock_token_mgr)
        result = api.send_text(["user1", "user2"], "Broadcast")

        self.assertEqual(result["errcode"], 0)
        call_kwargs = mock_req.call_args
        self.assertEqual(call_kwargs[1]["json"]["touser"], "user1|user2")

    @patch("gateway.api.message.requests.request")
    def test_send_image(self, mock_req):
        """Test sending image message."""
        from gateway.api.message import WeComMessageAPI

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_resp.raise_for_status.return_value = None
        mock_req.return_value = mock_resp

        api = WeComMessageAPI(self.mock_token_mgr)
        result = api.send_image("user1", "media_abc123")

        self.assertEqual(result["errcode"], 0)
        call_kwargs = mock_req.call_args
        self.assertEqual(call_kwargs[1]["json"]["msgtype"], "image")
        self.assertEqual(call_kwargs[1]["json"]["image"]["media_id"], "media_abc123")

    @patch("gateway.api.message.requests.request")
    def test_send_textcard(self, mock_req):
        """Test sending textcard message."""
        from gateway.api.message import WeComMessageAPI

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_resp.raise_for_status.return_value = None
        mock_req.return_value = mock_resp

        api = WeComMessageAPI(self.mock_token_mgr)
        result = api.send_textcard(
            "user1",
            "Card Title",
            "Card Description",
            "https://example.com/link",
        )

        self.assertEqual(result["errcode"], 0)
        call_kwargs = mock_req.call_args
        self.assertEqual(call_kwargs[1]["json"]["msgtype"], "textcard")
        self.assertEqual(call_kwargs[1]["json"]["textcard"]["title"], "Card Title")

    @patch("gateway.api.message.requests.request")
    def test_retry_on_token_expired(self, mock_req):
        """Test automatic token refresh on 42001 error."""
        from gateway.api.message import WeComMessageAPI

        # First call: token expired, second call: success
        mock_resp_expired = MagicMock()
        mock_resp_expired.json.return_value = {"errcode": 42001, "errmsg": "expired"}
        mock_resp_ok = MagicMock()
        mock_resp_ok.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_resp_ok.raise_for_status.return_value = None
        mock_resp_expired.raise_for_status.return_value = None

        mock_req.side_effect = [mock_resp_expired, mock_resp_ok]

        api = WeComMessageAPI(self.mock_token_mgr)
        result = api.send_text("user1", "test")

        # After refresh, token is still valid
        self.mock_token_mgr._refresh.assert_called_once()


class TestMessageHandler(unittest.TestCase):
    """Test webhook/message.py message parsing and dedup."""

    def test_parse_text_message(self):
        """Test parsing text message."""
        from gateway.webhook.message import parse_message_content

        raw = {
            "MsgType": "text",
            "FromUserName": "external_user_1",
            "ToUserName": "staff_user_1",
            "MsgId": "msg_001",
            "CreateTime": "1700000000",
            "Content": "Hello, this is a test message",
        }

        msg = parse_message_content(raw)

        self.assertEqual(msg["msgid"], "msg_001")
        self.assertEqual(msg["from_user"], "external_user_1")
        self.assertEqual(msg["msg_type"], "text")
        self.assertEqual(msg["content"], "Hello, this is a test message")

    def test_parse_image_message(self):
        """Test parsing image message."""
        from gateway.webhook.message import parse_message_content

        raw = {
            "MsgType": "image",
            "FromUserName": "ext_user_2",
            "ToUserName": "staff_1",
            "MsgId": "msg_002",
            "CreateTime": "1700000001",
            "MediaId": "media_img_123",
            "PicUrl": "https://wework.qpic.cn/pic.jpg",
        }

        msg = parse_message_content(raw)

        self.assertEqual(msg["msg_type"], "image")
        self.assertEqual(msg["content"]["media_id"], "media_img_123")
        self.assertEqual(msg["content"]["pic_url"], "https://wework.qpic.cn/pic.jpg")

    def test_parse_file_message(self):
        """Test parsing file message."""
        from gateway.webhook.message import parse_message_content

        raw = {
            "MsgType": "file",
            "FromUserName": "ext_user_3",
            "ToUserName": "staff_1",
            "MsgId": "msg_003",
            "CreateTime": "1700000002",
            "MediaId": "media_file_123",
            "FileName": "report.pdf",
            "FileSize": "102400",
        }

        msg = parse_message_content(raw)

        self.assertEqual(msg["msg_type"], "file")
        self.assertEqual(msg["content"]["file_name"], "report.pdf")
        self.assertEqual(msg["content"]["file_size"], "102400")

    def test_idempotency_duplicate_detection(self):
        """Test that duplicate messages are detected."""
        from gateway.webhook.message import is_message_duplicate, _processed_messages

        # Clear cache
        _processed_messages.clear()

        # First call: not duplicate
        result1 = is_message_duplicate("msg_test_001", window=300)
        self.assertFalse(result1)

        # Second call with same ID: duplicate
        result2 = is_message_duplicate("msg_test_001", window=300)
        self.assertTrue(result2)

        # Different ID: not duplicate
        result3 = is_message_duplicate("msg_test_002", window=300)
        self.assertFalse(result3)

    def test_get_message_id_for_dedup(self):
        """Test message ID extraction for dedup."""
        from gateway.webhook.message import get_message_id_for_dedup

        # Regular message with MsgId
        msg = {"MsgId": "12345"}
        msg_id = get_message_id_for_dedup(msg)
        self.assertEqual(msg_id, "12345")

        # Event without MsgId — should generate composite hash
        event = {
            "FromUserName": "user1",
            "CreateTime": "1700000000",
            "Event": "change_contact",
        }
        event_id = get_message_id_for_dedup(event)
        self.assertIsInstance(event_id, str)
        self.assertTrue(len(event_id) > 0)


class TestEventHandler(unittest.TestCase):
    """Test webhook/event.py event handling."""

    def test_handle_add_external_contact(self):
        """Test handling new external contact addition."""
        from gateway.webhook.event import handle_event_message

        msg_data = {
            "ToUserName": "corp_id",
            "FromUserName": "external_user_1",
            "CreateTime": "1700000000",
            "MsgType": "event",
            "Event": "change_external_contact",
            "ChangeType": "add_external_contact",
            "UserID": "staff_001",
            "ExternalUserID": "wm_external_001",
            "State": "channel_qr_001",
            "WelcomeCode": "welcome_code_abc",
        }

        result = handle_event_message(msg_data)

        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["action"], "add_external_contact")
        self.assertEqual(result["staff_userid"], "staff_001")
        self.assertEqual(result["external_userid"], "wm_external_001")
        self.assertEqual(result["state"], "channel_qr_001")
        self.assertEqual(result["trigger_sop"], "welcome")

    def test_handle_unhandled_event(self):
        """Test handling unknown event type."""
        from gateway.webhook.event import handle_event_message

        msg_data = {
            "MsgType": "event",
            "Event": "unknown_event_type",
        }

        result = handle_event_message(msg_data)
        self.assertEqual(result["status"], "unhandled_event")
        self.assertEqual(result["event"], "unknown_event_type")

    def test_handle_chat_dismiss(self):
        """Test handling group chat dismissal."""
        from gateway.webhook.event import handle_event_message

        msg_data = {
            "MsgType": "event",
            "Event": "change_external_chat",
            "ChangeType": "dismiss",
            "ChatId": "chat_group_001",
        }

        result = handle_event_message(msg_data)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["action"], "chat_dismiss")
        self.assertEqual(result["chat_id"], "chat_group_001")


class TestFlaskApp(unittest.TestCase):
    """Test Flask app routes."""

    def setUp(self):
        from gateway.app import create_app
        from gateway.config import Config

        # Disable actual token/crypto for unit tests
        self.app = create_app()
        self.app.config["WECOM_TOKEN"] = ""  # Skip signature verification
        self.client = self.app.test_client()

    def test_health_check(self):
        """Test health endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "wecom-gateway")

    def test_not_found(self):
        """Test 404 handler."""
        response = self.client.get("/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_webhook_post_text_message(self):
        """Test webhook POST receiving a text message."""
        msg_data = {
            "ToUserName": "corp_id",
            "FromUserName": "external_user_1",
            "CreateTime": "1700000000",
            "MsgType": "text",
            "MsgId": "test_msg_001",
            "Content": "Hello from test",
        }

        response = self.client.post(
            "/webhook/callback",
            data=json.dumps(msg_data),
            content_type="application/json",
        )

        # Should return "success" string
        self.assertEqual(response.status_code, 200)

    def test_webhook_post_image_message(self):
        """Test webhook POST receiving an image message."""
        msg_data = {
            "ToUserName": "corp_id",
            "FromUserName": "ext_user_2",
            "CreateTime": "1700000001",
            "MsgType": "image",
            "MsgId": "test_msg_002",
            "MediaId": "media_abc",
            "PicUrl": "https://example.com/img.jpg",
        }

        response = self.client.post(
            "/webhook/callback",
            data=json.dumps(msg_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
