"""
Tag SOP — 自动标签打标
触发：根据用户行为自动打标
"""
from sop.engine import SOPRule, TriggerType

def create_tag_sop() -> SOPRule:
    return SOPRule(
        id="SOP-TAG-001",
        name="自动标签打标",
        trigger_type=TriggerType.EVENT,
        trigger_config={"event": "customer_message"},
        actions=[
            {
                "type": "add_tag",
                "delay_seconds": 0,
                "tags": ["活跃用户"],
                "condition": "session_count >= 3",
            },
        ],
    )
