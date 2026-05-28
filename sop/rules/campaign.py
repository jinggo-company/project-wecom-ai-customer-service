"""
Campaign SOP — 营销活动精准触达
触发：满足特定标签/条件
"""
from sop.engine import SOPRule, TriggerType

def create_campaign_sop() -> SOPRule:
    return SOPRule(
        id="SOP-CAMPAIGN-001",
        name="营销活动精准触达",
        trigger_type=TriggerType.CONDITION,
        trigger_config={
            "tags": ["高价值"],
            "min_session_count": 5,
        },
        actions=[
            {
                "type": "send_message",
                "delay_seconds": 0,
                "message": "{{customer_name}} 您好！作为我们的重要客户，特为您准备了专属优惠：全场8折，仅限本周！点击领取 → {{coupon_link}}",
            },
            {
                "type": "notify_staff",
                "delay_seconds": 3600,
                "message": "已向高价值客户 {{customer_name}} 推送专属优惠，请注意跟进",
            },
            {
                "type": "add_tag",
                "delay_seconds": 0,
                "tags": ["已推送优惠"],
            },
        ],
    )
