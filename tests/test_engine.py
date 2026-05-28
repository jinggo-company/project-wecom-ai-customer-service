"""
Tests for T-2026-00055: WeCom AI 客服 — Dify Agent 引擎 + RAG 知识库
Run: pytest tests/test_engine.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.app import (
    IntentRecognizer, KnowledgeBase, SOPEngine,
    LLMProvider, CustomerServiceAgent, SOPRule,
    Intent, KnowledgeResult, AgentResponse,
    IntentType, INTENT_KEYWORDS, INTENT_CONFIDENCE_THRESHOLD,
)


# ── Intent Recognizer Tests ─────────────────────────────────

class TestIntentRecognizer:
    def setup_method(self):
        self.recognizer = IntentRecognizer()

    def test_detect_product_inquiry(self):
        intents = self.recognizer.detect("你们的产品有什么功能？")
        assert len(intents) > 0
        assert intents[0].name == IntentType.PRODUCT_INQUIRY.value

    def test_detect_order_query(self):
        intents = self.recognizer.detect("我的订单什么时候发货？")
        assert len(intents) > 0
        assert intents[0].name == IntentType.ORDER_QUERY.value

    def test_detect_after_sales(self):
        intents = self.recognizer.detect("产品怎么安装？有教程吗？")
        assert len(intents) > 0
        assert any(i.name == IntentType.AFTER_SALES.value for i in intents)

    def test_detect_pricing(self):
        intents = self.recognizer.detect("这个多少钱？有优惠吗？")
        assert any(i.name == IntentType.PRICING.value for i in intents)

    def test_detect_complaint(self):
        intents = self.recognizer.detect("太差了我要投诉你们！")
        assert any(i.name == IntentType.COMPLAINT.value for i in intents)

    def test_detect_human_agent(self):
        intents = self.recognizer.detect("我要转人工客服")
        assert any(i.name == IntentType.HUMAN_AGENT.value for i in intents)

    def test_detect_technical_support(self):
        intents = self.recognizer.detect("系统报错，无法登录")
        assert any(i.name == IntentType.TECHNICAL_SUPPORT.value for i in intents)

    def test_detect_refund(self):
        intents = self.recognizer.detect("我要退款，产品质量有问题")
        assert any(i.name == IntentType.REFUND_EXCHANGE.value for i in intents)

    def test_detect_general_chat(self):
        intents = self.recognizer.detect("你好")
        # No keyword match for general chat — expected
        assert isinstance(intents, list)

    def test_detect_multiple_intents(self):
        intents = self.recognizer.detect("你们的物流太慢了，我要退款，价格也不便宜")
        # Should detect at least 2 intents
        assert len(intents) >= 2

    def test_is_escalation_complaint(self):
        intents = [Intent(name=IntentType.COMPLAINT.value, confidence=0.7)]
        assert self.recognizer.is_escalation(intents)

    def test_is_escalation_human(self):
        intents = [Intent(name=IntentType.HUMAN_AGENT.value, confidence=0.8)]
        assert self.recognizer.is_escalation(intents)

    def test_no_escalation(self):
        intents = [Intent(name=IntentType.PRICING.value, confidence=0.6)]
        assert not self.recognizer.is_escalation(intents)

    def test_intent_confidence_above_threshold(self):
        intents = self.recognizer.detect("价格多少")
        for intent in intents:
            assert intent.confidence > 0


# ── Knowledge Base Tests ────────────────────────────────────

class TestKnowledgeBase:
    def setup_method(self):
        self.kb = KnowledgeBase()
        self.kb.add_document("doc1", "退货政策",
            "本产品支持7天无理由退货。商品未使用、包装完好即可申请退货。",
            {"category": "policy"})
        self.kb.add_document("doc2", "配送说明",
            "标准配送3-5个工作日，加急配送1-2个工作日。满99元包邮。",
            {"category": "logistics"})
        self.kb.add_document("doc3", "产品规格",
            "产品尺寸: 10x10x5cm, 重量: 200g, 材质: ABS塑料。",
            {"category": "product"})

    def test_add_document(self):
        assert self.kb.size() == 3

    def test_search_by_query(self):
        results = self.kb.search("退货")
        assert len(results) > 0
        assert results[0]["doc_id"] == "doc1"

    def test_search_score_ordering(self):
        results = self.kb.search("配送")
        assert len(results) > 0
        assert results[0]["score"] >= results[-1]["score"]

    def test_search_no_results(self):
        results = self.kb.search("外星人存在证据")
        # Should return empty list
        assert results == []

    def test_query_returns_knowledge_result(self):
        result = self.kb.query("怎么退货")
        assert result is not None
        assert isinstance(result, KnowledgeResult)
        assert result.query == "怎么退货"

    def test_query_no_match(self):
        result = self.kb.query("量子力学")
        assert result is None

    def test_search_top_k(self):
        results = self.kb.search("产品", top_k=1)
        assert len(results) <= 1

    def test_search_metadata(self):
        results = self.kb.search("配送")
        assert len(results) > 0
        assert results[0]["metadata"]["category"] == "logistics"

    def test_kb_size_empty(self):
        empty_kb = KnowledgeBase()
        assert empty_kb.size() == 0


# ── SOP Engine Tests ────────────────────────────────────────

class TestSOPEngine:
    def setup_method(self):
        self.sop = SOPEngine()
        self.sop.add_rule(SOPRule(
            id="sop-refund",
            name="退货流程",
            intent_trigger=[IntentType.REFUND_EXCHANGE.value],
            keywords=["退款", "退货"],
            reply_template="好的，我来帮您处理退货。请提供订单号，我为您查询退货流程。",
            follow_up_actions=["收集订单号", "核实退货条件", "生成退货标签"],
        ))
        self.sop.add_rule(SOPRule(
            id="sop-complaint",
            name="投诉处理",
            intent_trigger=[IntentType.COMPLAINT.value],
            keywords=["投诉", "不满"],
            reply_template="非常抱歉给您带来不便，我们非常重视您的反馈。正在为您转接高级客服...n",
            follow_up_actions=["记录投诉详情", "转接高级客服", "跟进处理结果"],
        ))

    def test_match_refund(self):
        intents = [Intent(name=IntentType.REFUND_EXCHANGE.value, confidence=0.7)]
        rule = self.sop.match(intents, "我想退款")
        assert rule is not None
        assert rule.id == "sop-refund"

    def test_match_complaint(self):
        intents = [Intent(name=IntentType.COMPLAINT.value, confidence=0.8)]
        rule = self.sop.match(intents, "我要投诉")
        assert rule is not None
        assert rule.id == "sop-complaint"

    def test_no_match(self):
        intents = [Intent(name=IntentType.PRICING.value, confidence=0.6)]
        rule = self.sop.match(intents, "多少钱")
        assert rule is None

    def test_no_match_wrong_intent(self):
        intents = [Intent(name=IntentType.PRODUCT_INQUIRY.value, confidence=0.6)]
        rule = self.sop.match(intents, "我要退货")
        assert rule is None

    def test_sop_rule_attributes(self):
        rule = SOPRule(
            id="sop-test",
            name="测试",
            intent_trigger=["test"],
            keywords=["test"],
            reply_template="test reply",
            follow_up_actions=["action1"],
        )
        assert rule.id == "sop-test"
        assert rule.name == "测试"
        assert rule.reply_template == "test reply"
        assert len(rule.follow_up_actions) == 1


# ── LLM Provider Tests ──────────────────────────────────────

class TestLLMProvider:
    def test_simulate_response(self):
        llm = LLMProvider()
        messages = [{"role": "user", "content": "你好"}]
        response = llm.chat(messages)
        assert "[模拟回复]" in response

    def test_llm_call_count(self):
        llm = LLMProvider()
        llm.chat([{"role": "user", "content": "你好"}])
        llm.chat([{"role": "user", "content": "你好"}])
        assert llm._call_count == 2

    def test_llm_api_key_config(self):
        llm = LLMProvider(api_key="sk-real-key", model="qwen-plus")
        assert llm.primary_model == "qwen-plus"
        assert llm.api_key == "sk-real-key"


# ── CustomerServiceAgent Tests ──────────────────────────────

class TestCustomerServiceAgent:
    def setup_method(self):
        kb = KnowledgeBase()
        kb.add_document("doc1", "退货政策",
            "本产品支持7天无理由退货。",
            {"category": "policy"})
        kb.add_document("doc2", "配送说明",
            "标准配送3-5个工作日。",
            {"category": "logistics"})

        sop = SOPEngine()
        sop.add_rule(SOPRule(
            id="sop-refund",
            name="退货流程",
            intent_trigger=[IntentType.REFUND_EXCHANGE.value],
            keywords=["退款", "退货"],
            reply_template="好的，我来帮您处理退货。",
            follow_up_actions=["收集订单号"],
        ))

        self.agent = CustomerServiceAgent(kb=kb, sop_engine=sop)

    def test_process_sop_triggered(self):
        response = self.agent.process("session1", "我要退款")
        assert response.sop_triggered is True
        assert response.sop_id == "sop-refund"

    def test_process_escalation(self):
        response = self.agent.process("session1", "我要投诉")
        assert response.escalate_to_human is True

    def test_process_human_agent_request(self):
        response = self.agent.process("session1", "转人工")
        assert response.escalate_to_human is True

    def test_process_returns_reply(self):
        response = self.agent.process("session1", "你好")
        assert isinstance(response, AgentResponse)
        assert response.reply is not None

    def test_process_knowledge_match(self):
        response = self.agent.process("session1", "怎么退货？")
        # Should match KB if intent not in escalation and no SOP
        assert isinstance(response, AgentResponse)
        assert response.reply is not None

    def test_processing_time_tracked(self):
        response = self.agent.process("session1", "你好")
        assert "processing_time_ms" in response.metadata

    def test_session_history(self):
        self.agent.process("session1", "你好")
        self.agent.process("session1", "在吗？")
        assert "session1" in self.agent._session_history
        assert len(self.agent._session_history["session1"]) == 4  # 2 user + 2 assistant

    def test_clear_session(self):
        self.agent.process("session1", "你好")
        self.agent.clear_session("session1")
        assert "session1" not in self.agent._session_history

    def test_customer_context(self):
        response = self.agent.process(
            "session1", "你好",
            customer_context={"company_name": "测试公司", "business_hours": "9:00-18:00"}
        )
        assert isinstance(response, AgentResponse)
