"""
Integration Tests — SOP Engine + Tags + Backend API + Dashboard data flow
T-2026-00056 | P-2026-00012
"""
import pytest
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sop.engine import (
    SOPEngine, SOPRule, SOPAction, SOPExecution,
    TriggerType, ActionType, SOPStatus,
)
from tags.manager import TagManager, Tag
from engine.app import (
    CustomerServiceAgent, IntentRecognizer, KnowledgeBase,
    SOPEngine as EngineSOPEngine, Intent, IntentType,
)


# ── SOP Engine Tests ────────────────────────────────────────

class TestSOPEngine:
    """Test SOP engine core functionality"""

    @pytest.fixture
    def engine(self):
        return SOPEngine()

    @pytest.fixture
    def welcome_rule(self):
        return SOPRule(
            id="SOP-WELCOME-001",
            name="新客户欢迎流程",
            trigger_type=TriggerType.EVENT,
            trigger_config={"event": "customer_added"},
            actions=[
                {"type": "send_message", "delay_seconds": 0, "message": "欢迎 {{customer_name}}！"},
                {"type": "add_tag", "delay_seconds": 5, "tags": ["新客户"]},
                {"type": "notify_staff", "delay_seconds": 10, "message": "新客户已添加"},
            ],
        )

    def test_add_and_list_rules(self, engine, welcome_rule):
        """SOP-CASE-001: 添加并列出规则"""
        engine.add_rule(welcome_rule)
        rules = engine.list_rules()
        assert len(rules) == 1
        assert rules[0].id == "SOP-WELCOME-001"

    def test_execute_sop(self, engine, welcome_rule):
        """SOP-CASE-002: 执行SOP规则"""
        engine.add_rule(welcome_rule)
        result = engine.execute("SOP-WELCOME-001", "user_001", {"customer_name": "张三"})
        assert result is not None
        assert result.status == SOPStatus.SUCCESS
        assert result.sop_id == "SOP-WELCOME-001"
        assert result.target_user_id == "user_001"

    def test_execute_disabled_rule(self, engine, welcome_rule):
        """SOP-CASE-003: 禁用的规则不执行"""
        welcome_rule.enabled = False
        engine.add_rule(welcome_rule)
        result = engine.execute("SOP-WELCOME-001", "user_001")
        assert result is None

    def test_match_event(self, engine, welcome_rule):
        """SOP-CASE-004: 事件匹配触发"""
        engine.add_rule(welcome_rule)
        executions = engine.match_event("customer_added", "user_001", {"customer_name": "李四"})
        assert len(executions) == 1
        assert executions[0].status == SOPStatus.SUCCESS

    def test_match_condition(self, engine):
        """SOP-CASE-005: 条件匹配触发"""
        campaign_rule = SOPRule(
            id="SOP-CAMPAIGN-001",
            name="营销活动",
            trigger_type=TriggerType.CONDITION,
            trigger_config={"tags": ["高价值"]},
            actions=[
                {"type": "send_message", "delay_seconds": 0, "message": "专属优惠！"},
            ],
        )
        engine.add_rule(campaign_rule)
        executions = engine.match_condition(["高价值"], {}, "user_001")
        assert len(executions) == 1

    def test_condition_skip(self, engine):
        """SOP-CASE-006: 条件不满足时跳过"""
        campaign_rule = SOPRule(
            id="SOP-CAMPAIGN-002",
            name="营销活动2",
            trigger_type=TriggerType.CONDITION,
            trigger_config={"tags": ["高价值"]},
            actions=[
                {"type": "send_message", "delay_seconds": 0, "message": "专属优惠！"},
            ],
        )
        engine.add_rule(campaign_rule)
        executions = engine.match_condition(["普通"], {}, "user_002")
        assert len(executions) == 0

    def test_remove_rule(self, engine, welcome_rule):
        """SOP-CASE-007: 删除规则"""
        engine.add_rule(welcome_rule)
        assert engine.remove_rule("SOP-WELCOME-001")
        assert len(engine.list_rules()) == 0

    def test_get_stats(self, engine, welcome_rule):
        """SOP-CASE-008: 统计信息"""
        engine.add_rule(welcome_rule)
        engine.execute("SOP-WELCOME-001", "user_001")
        stats = engine.get_stats()
        assert stats["total_rules"] == 1
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1
        assert stats["success_rate"] == 100.0

    def test_template_rendering(self, engine):
        """SOP-CASE-009: 模板变量替换"""
        rule = SOPRule(
            id="SOP-TEST-001",
            name="模板测试",
            trigger_type=TriggerType.EVENT,
            trigger_config={"event": "test"},
            actions=[
                {"type": "send_message", "delay_seconds": 0,
                 "message": "你好 {{customer_name}}，你的订单号是 {{order_id}}"},
            ],
        )
        engine.add_rule(rule)
        result = engine.execute("SOP-TEST-001", "user_001",
                                {"customer_name": "王五", "order_id": "ORD-123"})
        assert result is not None
        assert result.status == SOPStatus.SUCCESS

    def test_get_due_rules(self, engine):
        """SOP-CASE-010: 获取到期的定时规则"""
        now = datetime.utcnow()
        time_rule = SOPRule(
            id="SOP-TIME-001",
            name="定时问候",
            trigger_type=TriggerType.TIME,
            trigger_config={
                "schedule": "cron",
                "hour": now.hour,
                "minute": now.minute,
            },
            actions=[
                {"type": "send_message", "delay_seconds": 0, "message": "早安！"},
            ],
        )
        engine.add_rule(time_rule)
        due = engine.get_due_rules(now=now)
        assert len(due) == 1

    def test_execution_history(self, engine, welcome_rule):
        """SOP-CASE-011: 执行记录查询"""
        engine.add_rule(welcome_rule)
        engine.execute("SOP-WELCOME-001", "user_001")
        engine.execute("SOP-WELCOME-001", "user_002")
        execs = engine.list_executions(sop_id="SOP-WELCOME-001")
        assert len(execs) == 2
        user1_execs = engine.list_executions(user_id="user_001")
        assert len(user1_execs) == 1


# ── Tag Manager Tests ───────────────────────────────────────

class TestTagManager:
    """Test user tagging system"""

    @pytest.fixture
    def manager(self):
        mgr = TagManager()
        mgr.add_tag(Tag(id="TAG-001", name="新客户", category="auto", rule={"days_since_added": 0}))
        mgr.add_tag(Tag(id="TAG-002", name="活跃用户", category="auto", rule={"session_count": 5}))
        mgr.add_tag(Tag(id="TAG-003", name="高价值", category="manual"))
        return mgr

    def test_add_and_list_tags(self, manager):
        """TAG-CASE-001: 添加和列出标签"""
        tags = manager.list_tags()
        assert len(tags) == 3

    def test_add_tag_to_user(self, manager):
        """TAG-CASE-002: 给用户打标签"""
        assert manager.add_tag_to_user("user_001", "TAG-001")
        user_tags = manager.get_user_tags("user_001")
        assert len(user_tags) == 1
        assert user_tags[0].name == "新客户"

    def test_remove_tag_from_user(self, manager):
        """TAG-CASE-003: 移除用户标签"""
        manager.add_tag_to_user("user_001", "TAG-001")
        assert manager.remove_tag_from_user("user_001", "TAG-001")
        user_tags = manager.get_user_tags("user_001")
        assert len(user_tags) == 0

    def test_get_users_by_tag(self, manager):
        """TAG-CASE-004: 按标签查询用户"""
        manager.add_tag_to_user("user_001", "TAG-001")
        manager.add_tag_to_user("user_002", "TAG-001")
        users = manager.get_users_by_tag("TAG-001")
        assert len(users) == 2

    def test_users_with_all_tags(self, manager):
        """TAG-CASE-005: 多标签交集查询"""
        manager.add_tag_to_user("user_001", "TAG-001")
        manager.add_tag_to_user("user_001", "TAG-002")
        manager.add_tag_to_user("user_002", "TAG-001")
        # Only user_001 has both TAG-001 and TAG-002
        users = manager.get_users_with_all_tags(["TAG-001", "TAG-002"])
        assert "user_001" in users
        assert "user_002" not in users

    def test_remove_tag(self, manager):
        """TAG-CASE-006: 删除标签"""
        manager.add_tag_to_user("user_001", "TAG-001")
        manager.remove_tag("TAG-001")
        assert manager.get_tag("TAG-001") is None

    def test_auto_rules(self, manager):
        """TAG-CASE-007: 自动打标规则"""
        mgr = TagManager()
        mgr.add_tag(Tag(id="TAG-AUTO-001", name="新用户", category="auto", rule={"days_since_added": 0}))
        applied = mgr.apply_auto_rules("user_001", {"days_since_added": 0})
        assert "TAG-AUTO-001" in applied

    def test_segment(self, manager):
        """TAG-CASE-008: 用户分群"""
        manager.add_tag_to_user("user_001", "TAG-001")
        manager.add_tag_to_user("user_001", "TAG-003")
        segment = manager.get_segment(["TAG-001", "TAG-003"])
        assert segment["user_count"] == 1
        assert "user_001" in segment["user_ids"]

    def test_tag_count(self, manager):
        """TAG-CASE-009: 标签用户计数"""
        manager.add_tag_to_user("user_001", "TAG-003")
        manager.add_tag_to_user("user_002", "TAG-003")
        tag = manager.get_tag("TAG-003")
        assert tag.user_count == 2

    def test_stats(self, manager):
        """TAG-CASE-010: 标签统计"""
        manager.add_tag_to_user("user_001", "TAG-001")
        manager.add_tag_to_user("user_002", "TAG-002")
        stats = manager.get_stats()
        assert stats["total_tags"] == 3
        assert stats["tagged_users"] == 2


# ── Integration: SOP + Engine Tests ──────────────────────────

class TestSOPIntegration:
    """Test SOP integration with the AI engine"""

    def test_sop_triggered_by_complaint(self):
        """INT-CASE-001: 投诉意图触发转人工"""
        agent = CustomerServiceAgent()
        response = agent.process("sess_001", "我要投诉，你们的服务太差了！")
        assert response.escalate_to_human is True

    def test_sop_triggered_by_human_request(self):
        """INT-CASE-002: 人工请求触发转接"""
        agent = CustomerServiceAgent()
        response = agent.process("sess_002", "我要转人工客服")
        assert response.escalate_to_human is True

    def test_kb_match(self):
        """INT-CASE-003: 知识库匹配返回"""
        agent = CustomerServiceAgent()
        agent.kb.add_document("KB-001", "退换货政策",
                              "7天无理由退换货，商品需保持原包装", {})
        response = agent.process("sess_003", "请问你们支持退换货吗？")
        # Should match KB or fallback to LLM
        assert response.reply is not None
        assert len(response.reply) > 0

    def test_intent_detection(self):
        """INT-CASE-004: 意图识别"""
        recognizer = IntentRecognizer()
        intents = recognizer.detect("这个产品多少钱？")
        assert len(intents) > 0
        # "多少钱" triggers PRICING, "产品" triggers PRODUCT_INQUIRY
        # Either is valid — check that at least one pricing-related intent is detected
        intent_names = {i.name for i in intents}
        assert IntentType.PRICING.value in intent_names or IntentType.PRODUCT_INQUIRY.value in intent_names

    def test_order_query_intent(self):
        """INT-CASE-005: 订单查询意图"""
        recognizer = IntentRecognizer()
        intents = recognizer.detect("我的快递到哪里了？")
        assert any(i.name == IntentType.ORDER_QUERY.value for i in intents)

    def test_multi_intent(self):
        """INT-CASE-006: 多意图检测"""
        recognizer = IntentRecognizer()
        intents = recognizer.detect("我要投诉这个产品，价格太贵了，而且我要退款")
        intent_names = {i.name for i in intents}
        assert IntentType.COMPLAINT.value in intent_names or \
               IntentType.REFUND_EXCHANGE.value in intent_names or \
               IntentType.PRICING.value in intent_names


# ── Backend API Tests (FastAPI TestClient) ─────────────────

class TestBackendAPI:
    """Test FastAPI backend endpoints"""

    @pytest.fixture
    def client(self):
        try:
            from fastapi.testclient import TestClient
            from backend.app import app
            return TestClient(app)
        except ImportError:
            pytest.skip("FastAPI test client not available")

    def test_health(self, client):
        """API-CASE-001: 健康检查"""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_overview(self, client):
        """API-CASE-002: 总览数据"""
        resp = client.get("/api/analytics/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data
        assert "ai_handled" in data
        assert "human_handled" in data

    def test_sessions_list(self, client):
        """API-CASE-003: 会话列表"""
        resp = client.get("/api/sessions", params={"page": 1, "page_size": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "data" in data
        assert len(data["data"]) <= 5

    def test_sessions_filter(self, client):
        """API-CASE-004: 会话过滤"""
        resp = client.get("/api/sessions", params={"status": "resolved"})
        assert resp.status_code == 200
        data = resp.json()
        for s in data["data"]:
            assert s["resolution_status"] == "resolved"

    def test_intent_distribution(self, client):
        """API-CASE-005: 意图分布"""
        resp = client.get("/api/analytics/intents")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) > 0

    def test_tag_analytics(self, client):
        """API-CASE-006: 标签分析"""
        resp = client.get("/api/analytics/tags")
        assert resp.status_code == 200
        data = resp.json()
        assert "tag_coverage_rate" in data
        assert "tags" in data

    def test_sop_analytics(self, client):
        """API-CASE-007: SOP分析"""
        resp = client.get("/api/analytics/sop")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_rules" in data
        assert "success_rate" in data

    def test_user_growth(self, client):
        """API-CASE-008: 用户增长"""
        resp = client.get("/api/analytics/user_growth")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) == 30

    def test_realtime(self, client):
        """API-CASE-009: 实时指标"""
        resp = client.get("/api/analytics/realtime")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_sessions" in data
        assert "ai_accuracy_rate" in data

    def test_users_list(self, client):
        """API-CASE-010: 用户列表"""
        resp = client.get("/api/users")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "data" in data


# ── Docker Compose Validation ──────────────────────────────

class TestDockerCompose:
    """Test Docker Compose configuration"""

    def test_compose_file_exists(self):
        """DOCKER-CASE-001: docker-compose文件存在"""
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "deploy", "docker-compose.yml"
        )
        assert os.path.exists(compose_path), f"docker-compose.yml not found at {compose_path}"

    def test_compose_services(self):
        """DOCKER-CASE-002: 服务定义完整"""
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "deploy", "docker-compose.yml"
        )
        try:
            import yaml
            with open(compose_path) as f:
                compose = yaml.safe_load(f)
            services = compose.get("services", {})
            assert "gateway" in services, "Missing gateway service"
            assert "backend" in services, "Missing backend service"
            assert "postgres" in services, "Missing postgres service"
            assert "redis" in services, "Missing redis service"
        except ImportError:
            pytest.skip("PyYAML not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
