"""
Welcome SOP — 新客户欢迎流程
触发：用户首次添加企微
"""
from sop.engine import SOPRule, TriggerType

def create_welcome_sop() -> SOPRule:
    return SOPRule(
        id="SOP-WELCOME-001",
        name="新客户欢迎流程",
        trigger_type=TriggerType.EVENT,
        trigger_config={"event": "customer_added"},
        actions=[
            {
                "type": "send_message",
                "delay_seconds": 0,
                "message": "您好 {{customer_name}}，欢迎加入！我是您的专属客服助手，有任何问题随时联系我 😊",
            },
            {
                "type": "add_tag",
                "delay_seconds": 5,
                "tags": ["新客户"],
            },
            {
                "type": "notify_staff",
                "delay_seconds": 10,
                "message": "新客户 {{customer_name}} 已添加，请及时跟进",
            },
        ],
    )
