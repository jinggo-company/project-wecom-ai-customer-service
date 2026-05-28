"""
Follow-up SOP — 定期跟进提醒
触发：添加后第1天、第3天、第7天
"""
from sop.engine import SOPRule, TriggerType

def create_followup_sop() -> SOPRule:
    return SOPRule(
        id="SOP-FOLLOWUP-001",
        name="客户定期跟进",
        trigger_type=TriggerType.EVENT,
        trigger_config={"event": "customer_added"},
        actions=[
            {
                "type": "send_message",
                "delay_seconds": 86400,  # 24小时后
                "message": "您好 {{customer_name}}，使用我们的产品还满意吗？有任何问题都可以告诉我~",
                "condition": "session_count <= 1",
            },
            {
                "type": "send_message",
                "delay_seconds": 259200,  # 3天后
                "message": "{{customer_name}} 您好，感谢您的关注！我们近期有一些优惠活动，想了解吗？",
                "condition": "session_count <= 2",
            },
            {
                "type": "send_message",
                "delay_seconds": 604800,  # 7天后
                "message": "{{customer_name}} 您好，一周了，想了解一下您的使用体验。如需任何帮助请随时联系~",
            },
            {
                "type": "add_tag",
                "delay_seconds": 604800,
                "tags": ["已跟进"],
            },
        ],
    )
