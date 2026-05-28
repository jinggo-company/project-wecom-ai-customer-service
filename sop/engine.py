"""
SOP Engine Core — Standard Operating Procedure automation for WeCom AI Customer Service
T-2026-00056 | P-2026-00012

SOP 自动化引擎：欢迎语、跟进提醒、用户标签、精准触达
支持时间触发、事件触发、条件触发三种模式
"""
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    TIME = "time"           # 固定时间点 / 周期
    EVENT = "event"         # 用户行为事件
    CONDITION = "condition" # 满足标签/属性条件


class SOPStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SOPRule:
    """SOP 规则定义"""
    id: str
    name: str
    trigger_type: TriggerType
    trigger_config: dict = field(default_factory=dict)  # 触发条件配置
    actions: list = field(default_factory=list)          # 执行动作列表
    enabled: bool = True
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["trigger_type"] = self.trigger_type.value
        if self.created_at:
            d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SOPRule":
        trigger_type = TriggerType(data["trigger_type"])
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            id=data["id"],
            name=data["name"],
            trigger_type=trigger_type,
            trigger_config=data.get("trigger_config", {}),
            actions=data.get("actions", []),
            enabled=data.get("enabled", True),
            created_at=created_at,
        )


@dataclass
class SOPExecution:
    """SOP 执行记录"""
    id: str
    sop_id: str
    target_user_id: str
    status: SOPStatus
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        if self.executed_at:
            d["executed_at"] = self.executed_at.isoformat()
        if self.completed_at:
            d["completed_at"] = self.completed_at.isoformat()
        return d


# ── Action Types ────────────────────────────────────────────

class ActionType(str, Enum):
    SEND_MESSAGE = "send_message"
    ADD_TAG = "add_tag"
    NOTIFY_STAFF = "notify_staff"
    SEND_TEMPLATE = "send_template"
    UPDATE_FIELD = "update_field"
    WEBHOOK_CALL = "webhook_call"


@dataclass
class SOPAction:
    """SOP 执行动作"""
    type: ActionType
    delay_seconds: int = 0
    template: str = ""
    message: str = ""
    tags: list = field(default_factory=list)
    condition: str = ""
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SOPAction":
        return cls(
            type=ActionType(data["type"]),
            delay_seconds=data.get("delay_seconds", 0),
            template=data.get("template", ""),
            message=data.get("message", ""),
            tags=data.get("tags", []),
            condition=data.get("condition", ""),
            config=data.get("config", {}),
        )


# ── SOP Engine ──────────────────────────────────────────────

class SOPEngine:
    """
    SOP 引擎核心 — 规则匹配 + 动作调度 + 执行追踪
    """

    def __init__(self, wecom_send_fn: Callable = None, tag_add_fn: Callable = None,
                 notify_fn: Callable = None, webhook_fn: Callable = None):
        self._rules: dict[str, SOPRule] = {}
        self._executions: dict[str, SOPExecution] = {}
        self._wecom_send = wecom_send_fn or self._default_send
        self._tag_add = tag_add_fn or self._default_tag
        self._notify = notify_fn or self._default_notify
        self._webhook = webhook_fn or self._default_webhook
        self._execution_counter = 0

    def add_rule(self, rule: SOPRule):
        """Add or update an SOP rule."""
        self._rules[rule.id] = rule
        logger.info(f"SOP rule added: {rule.id} — {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"SOP rule removed: {rule_id}")
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[SOPRule]:
        return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = False) -> list[SOPRule]:
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    def list_executions(self, sop_id: str = None, user_id: str = None) -> list[SOPExecution]:
        execs = list(self._executions.values())
        if sop_id:
            execs = [e for e in execs if e.sop_id == sop_id]
        if user_id:
            execs = [e for e in execs if e.target_user_id == user_id]
        return execs

    def execute(self, rule_id: str, user_id: str, context: dict = None) -> Optional[SOPExecution]:
        """Execute an SOP rule for a specific user."""
        rule = self._rules.get(rule_id)
        if not rule or not rule.enabled:
            logger.warning(f"SOP rule {rule_id} not found or disabled")
            return None

        self._execution_counter += 1
        exec_id = f"{rule_id}-E{self._execution_counter:06d}"
        execution = SOPExecution(
            id=exec_id,
            sop_id=rule_id,
            target_user_id=user_id,
            status=SOPStatus.RUNNING,
            executed_at=datetime.utcnow(),
        )
        self._executions[exec_id] = execution

        try:
            results = []
            for action_data in rule.actions:
                action = SOPAction.from_dict(action_data) if isinstance(action_data, dict) else action_data

                # Check condition
                if action.condition and not self._evaluate_condition(action.condition, context):
                    logger.info(f"Action skipped (condition not met): {action.type.value}")
                    continue

                # Execute with delay
                if action.delay_seconds > 0:
                    # In production: schedule via Celery
                    logger.info(f"Scheduling action {action.type.value} with {action.delay_seconds}s delay")
                    continue

                result = self._run_action(action, user_id, context)
                results.append({"action": action.type.value, "result": result})

            execution.status = SOPStatus.SUCCESS
            execution.completed_at = datetime.utcnow()
            execution.result = {"actions": results}
            logger.info(f"SOP execution {exec_id} completed successfully")
            return execution

        except Exception as e:
            execution.status = SOPStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            logger.error(f"SOP execution {exec_id} failed: {e}")
            return execution

    def match_event(self, event_type: str, user_id: str, context: dict = None) -> list[SOPExecution]:
        """Match event-triggered SOP rules and execute them."""
        executions = []
        for rule in self.list_rules(enabled_only=True):
            if rule.trigger_type != TriggerType.EVENT:
                continue
            event = rule.trigger_config.get("event", "")
            if event == event_type:
                exec_result = self.execute(rule.id, user_id, context)
                if exec_result:
                    executions.append(exec_result)
        return executions

    def match_condition(self, user_tags: list[str], user_attrs: dict, user_id: str) -> list[SOPExecution]:
        """Match condition-triggered SOP rules."""
        executions = []
        for rule in self.list_rules(enabled_only=True):
            if rule.trigger_type != TriggerType.CONDITION:
                continue
            required_tags = rule.trigger_config.get("tags", [])
            if required_tags and all(t in user_tags for t in required_tags):
                exec_result = self.execute(rule.id, user_id, {"tags": user_tags, **user_attrs})
                if exec_result:
                    executions.append(exec_result)
        return executions

    def get_due_rules(self, now: datetime = None) -> list[SOPRule]:
        """Get time-triggered rules that are due now."""
        now = now or datetime.utcnow()
        due = []
        for rule in self.list_rules(enabled_only=True):
            if rule.trigger_type != TriggerType.TIME:
                continue
            config = rule.trigger_config
            if config.get("schedule") == "cron":
                hour = config.get("hour")
                minute = config.get("minute", 0)
                if now.hour == hour and now.minute == minute:
                    due.append(rule)
            elif config.get("schedule") == "interval":
                last_run = config.get("last_run")
                interval_hours = config.get("interval_hours", 24)
                if not last_run or (now - last_run).total_seconds() >= interval_hours * 3600:
                    due.append(rule)
        return due

    # ── Internal helpers ──────────────────────────────────────

    def _run_action(self, action: SOPAction, user_id: str, context: dict = None) -> dict:
        """Execute a single SOP action."""
        ctx = context or {}
        if action.type == ActionType.SEND_MESSAGE:
            msg = self._render_template(action.message, ctx)
            return self._wecom_send(user_id, msg)
        elif action.type == ActionType.ADD_TAG:
            return self._tag_add(user_id, action.tags)
        elif action.type == ActionType.NOTIFY_STAFF:
            msg = self._render_template(action.message, ctx)
            return self._notify(msg)
        elif action.type == ActionType.WEBHOOK_CALL:
            return self._webhook(action.config.get("url", ""), ctx)
        else:
            return {"status": "unsupported", "action": action.type.value}

    def _render_template(self, text: str, context: dict) -> str:
        """Simple template rendering with {{variable}} placeholders."""
        if not context:
            return text
        result = text
        for key, value in context.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def _evaluate_condition(self, condition: str, context: dict = None) -> bool:
        """Evaluate a simple condition string."""
        if not context:
            return False
        # Simple condition: "session_count <= 1" or "tag == 'vip'"
        ctx = context or {}
        try:
            # Safe eval for simple expressions
            allowed = {"session_count": ctx.get("session_count", 0),
                       "total_spend": ctx.get("total_spend", 0),
                       "days_since_added": ctx.get("days_since_added", 999)}
            return bool(eval(condition, {"__builtins__": {}}, allowed))
        except Exception:
            return False

    def _default_send(self, user_id: str, message: str) -> dict:
        return {"status": "simulated", "user_id": user_id, "message_len": len(message)}

    def _default_tag(self, user_id: str, tags: list) -> dict:
        return {"status": "simulated", "user_id": user_id, "tags": tags}

    def _default_notify(self, message: str) -> dict:
        return {"status": "simulated", "message": message}

    def _default_webhook(self, url: str, data: dict) -> dict:
        return {"status": "simulated", "url": url, "data_keys": list(data.keys())}

    def get_stats(self) -> dict:
        """Get SOP execution statistics."""
        total = len(self._executions)
        success = sum(1 for e in self._executions.values() if e.status == SOPStatus.SUCCESS)
        failed = sum(1 for e in self._executions.values() if e.status == SOPStatus.FAILED)
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "total_executions": total,
            "successful_executions": success,
            "failed_executions": failed,
            "success_rate": round(success / max(total, 1) * 100, 1),
        }
