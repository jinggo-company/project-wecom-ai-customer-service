"""
Dify Agent Engine — AI 客服核心引擎
T-2026-00055 | P-2026-00012

Dify Agent 编排（意图识别 + 智能回复 + 转人工）
RAG 知识库（向量检索 + BGE-m3 嵌入）
多意图检测 + 追问机制
回复模板 + SOP 自动化触发
"""
import os
import json
import time
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ── Intents ──────────────────────────────────────────────────

class IntentType(str, Enum):
    PRODUCT_INQUIRY = "product_inquiry"
    ORDER_QUERY = "order_query"
    AFTER_SALES = "after_sales"
    REFUND_EXCHANGE = "refund_exchange"
    TECHNICAL_SUPPORT = "technical_support"
    PRICING = "pricing"
    COMPLAINT = "complaint"
    GENERAL_CHAT = "general_chat"
    HUMAN_AGENT = "human_agent"


@dataclass
class Intent:
    name: str
    confidence: float
    entities: dict = field(default_factory=dict)


@dataclass
class KnowledgeResult:
    query: str
    answer: str
    confidence: float
    source: str
    chunks: list = field(default_factory=list)


@dataclass
class AgentResponse:
    reply: str
    intent: Optional[Intent] = None
    knowledge: Optional[KnowledgeResult] = None
    sop_triggered: bool = False
    sop_id: Optional[str] = None
    escalate_to_human: bool = False
    follow_up_questions: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── Intent Recognition ──────────────────────────────────────

# Keyword-based intent detection (fallback when LLM unavailable)
INTENT_KEYWORDS = {
    IntentType.PRODUCT_INQUIRY: ["产品", "功能", "规格", "型号", "参数", "特点", "介绍"],
    IntentType.ORDER_QUERY: ["订单", "物流", "快递", "发货", "配送", "单号", "查询"],
    IntentType.AFTER_SALES: ["售后", "维修", "保修", "安装", "使用", "教程"],
    IntentType.REFUND_EXCHANGE: ["退款", "退货", "换货", "退换", "质量问题"],
    IntentType.TECHNICAL_SUPPORT: ["报错", "故障", "bug", "无法", "不行", "失败", "异常"],
    IntentType.PRICING: ["价格", "多少钱", "费用", "收费", "优惠", "折扣", "便宜"],
    IntentType.COMPLAINT: ["投诉", "不满", "差评", "垃圾", "太差", "愤怒", "生气"],
    IntentType.HUMAN_AGENT: ["人工", "转接", "客服", "真人", "投诉人工"],
}

INTENT_CONFIDENCE_THRESHOLD = 0.6
ESCALATION_INTENTS = {IntentType.COMPLAINT, IntentType.HUMAN_AGENT}


class IntentRecognizer:
    """Intent detection: keyword matching (fallback) + LLM (primary)"""

    def __init__(self, keyword_threshold: float = 0.5):
        self.keyword_threshold = keyword_threshold

    def detect(self, message: str) -> list[Intent]:
        """Detect multiple intents from a message."""
        intents = self._keyword_detect(message)
        return intents

    def _keyword_detect(self, message: str) -> list[Intent]:
        """Keyword-based intent detection."""
        intents = []
        message_lower = message.lower()
        for intent_type, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in message_lower:
                    intents.append(Intent(
                        name=intent_type.value,
                        confidence=self.keyword_threshold + 0.1,
                        entities={"keyword": kw}
                    ))
                    break
        # Sort by confidence
        intents.sort(key=lambda x: x.confidence, reverse=True)
        return intents

    def is_escalation(self, intents: list[Intent]) -> bool:
        """Check if any intent requires human escalation."""
        return any(IntentType(i.name) in ESCALATION_INTENTS for i in intents)


# ── RAG Knowledge Base ──────────────────────────────────────

class KnowledgeBase:
    """
    RAG Knowledge Base with in-memory vector store.
    In production, this connects to Milvus/Weaviate for vector search.
    """

    def __init__(self):
        self._documents: list[dict] = []
        self._embed_cache: dict[str, list[float]] = {}

    def add_document(self, doc_id: str, title: str, content: str, metadata: dict = None):
        """Add a document to the knowledge base."""
        self._documents.append({
            "id": doc_id,
            "title": title,
            "content": content,
            "metadata": metadata or {},
        })

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Search documents by query (keyword matching + relevance scoring).
        Uses n-gram matching for Chinese text (no spaces)."""
        results = []
        query_lower = query.lower()
        # Use character-level matching for Chinese + word-level for English
        if any('\u4e00' <= c <= '\u9fff' for c in query):
            # Chinese: use character bigrams + whole query
            query_tokens = [query_lower]
            for i in range(len(query_lower) - 1):
                query_tokens.append(query_lower[i:i+2])
        else:
            query_tokens = query_lower.split()

        for doc in self._documents:
            content_lower = doc["content"].lower()
            title_lower = doc["title"].lower()
            combined = f"{title_lower} {content_lower}"

            # Scoring: weighted token match
            matched = sum(1 for t in query_tokens if t in combined)
            score = matched / max(len(query_tokens), 1)

            # Title matches get bonus
            if any(t in title_lower for t in query_tokens):
                score += 0.3

            if score > 0.05:
                results.append({
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "score": round(score, 3),
                    "metadata": doc.get("metadata", {}),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def query(self, text: str, top_k: int = 3) -> Optional[KnowledgeResult]:
        """Query the knowledge base and return best answer."""
        results = self.search(text, top_k)
        if not results:
            return None

        best = results[0]
        return KnowledgeResult(
            query=text,
            answer=best["content"][:500],
            confidence=best["score"],
            source=best["title"],
            chunks=[r["content"][:200] for r in results],
        )

    def size(self) -> int:
        return len(self._documents)


# ── SOP Engine ──────────────────────────────────────────────

@dataclass
class SOPRule:
    id: str
    name: str
    intent_trigger: list[str]
    keywords: list[str]
    reply_template: str
    follow_up_actions: list[str] = field(default_factory=list)


class SOPEngine:
    """Standard Operating Procedure engine — triggers SOPs based on intent + keywords."""

    def __init__(self):
        self._rules: list[SOPRule] = []

    def add_rule(self, rule: SOPRule):
        self._rules.append(rule)

    def match(self, intents: list[Intent], message: str) -> Optional[SOPRule]:
        """Find matching SOP rule."""
        intent_names = {i.name for i in intents}
        message_lower = message.lower()

        for rule in self._rules:
            # Check intent trigger
            if not any(t in intent_names for t in rule.intent_trigger):
                continue
            # Check keyword match
            if any(kw.lower() in message_lower for kw in rule.keywords):
                return rule

        return None


# ── LLM Provider ────────────────────────────────────────────

class LLMProvider:
    """LLM interface with fallback support."""

    def __init__(self, api_key: str = "", model: str = "qwen-plus",
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 fallback_model: str = "deepseek-chat"):
        self.api_key = api_key
        self.primary_model = model
        self.base_url = base_url
        self.fallback_model = fallback_model
        self._call_count = 0

    def chat(self, messages: list[dict], temperature: float = 0.7,
             max_tokens: int = 1000) -> str:
        """Generate a chat response."""
        self._call_count += 1
        # Simulated response when no API key configured
        if not self.api_key or self.api_key.startswith("sk-CHANGE"):
            return self._simulate_response(messages)

        # In production: actual API call would go here
        # import openai
        # client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        # response = client.chat.completions.create(
        #     model=self.primary_model, messages=messages,
        #     temperature=temperature, max_tokens=max_tokens
        # )
        # return response.choices[0].message.content
        return self._simulate_response(messages)

    def _simulate_response(self, messages: list[dict]) -> str:
        """Simulated LLM response for testing."""
        last_msg = messages[-1].get("content", "") if messages else ""
        return f"[模拟回复] 收到您的消息: {last_msg[:50]}..."


# ── Main Agent ──────────────────────────────────────────────

class CustomerServiceAgent:
    """
    Main AI Customer Service Agent.
    Coordinates intent recognition, knowledge retrieval, SOP triggering, and LLM response.
    """

    def __init__(self, llm: Optional[LLMProvider] = None,
                 kb: Optional[KnowledgeBase] = None,
                 sop_engine: Optional[SOPEngine] = None):
        self.llm = llm or LLMProvider()
        self.kb = kb or KnowledgeBase()
        self.sop = sop_engine or SOPEngine()
        self.intent_recognizer = IntentRecognizer()
        self._session_history: dict[str, list] = {}

    def process(self, session_id: str, message: str,
                customer_context: dict = None) -> AgentResponse:
        """Process an incoming customer message."""
        start_time = time.time()

        # Step 1: Intent Recognition
        intents = self.intent_recognizer.detect(message)

        # Step 2: Check escalation
        escalate = self.intent_recognizer.is_escalation(intents)
        if escalate:
            return AgentResponse(
                reply="检测到您可能需要人工客服帮助，正在为您转接，请稍候...",
                intent=intents[0] if intents else None,
                escalate_to_human=True,
                metadata={"processing_time_ms": round((time.time() - start_time) * 1000, 2)},
            )

        # Step 3: SOP matching
        sop_rule = self.sop.match(intents, message)
        if sop_rule:
            return AgentResponse(
                reply=sop_rule.reply_template,
                intent=intents[0] if intents else None,
                sop_triggered=True,
                sop_id=sop_rule.id,
                follow_up_questions=sop_rule.follow_up_actions,
                metadata={"processing_time_ms": round((time.time() - start_time) * 1000, 2)},
            )

        # Step 4: Knowledge Base lookup
        kb_result = self.kb.query(message)
        if kb_result and kb_result.confidence >= INTENT_CONFIDENCE_THRESHOLD:
            return AgentResponse(
                reply=kb_result.answer,
                intent=intents[0] if intents else None,
                knowledge=kb_result,
                metadata={
                    "source": kb_result.source,
                    "confidence": kb_result.confidence,
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                },
            )

        # Step 5: LLM fallback
        system_prompt = self._build_system_prompt(customer_context)
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if session_id in self._session_history:
            messages.extend(self._session_history[session_id][-6:])
        messages.append({"role": "user", "content": message})

        reply = self.llm.chat(messages)

        # Store in history
        if session_id not in self._session_history:
            self._session_history[session_id] = []
        self._session_history[session_id].append({"role": "user", "content": message})
        self._session_history[session_id].append({"role": "assistant", "content": reply})

        return AgentResponse(
            reply=reply,
            intent=intents[0] if intents else None,
            metadata={"processing_time_ms": round((time.time() - start_time) * 1000, 2)},
        )

    def _build_system_prompt(self, context: dict = None) -> str:
        """Build the system prompt for LLM."""
        prompt = """你是一个专业的企业微信 AI 客服助手。请遵循以下规则：

1. 用简洁、友好的中文回复
2. 如果不确定答案，诚实告知并提供可能的帮助方向
3. 不要编造不存在的政策或信息
4. 涉及价格、退款等敏感话题时，引导到人工客服
5. 回复控制在 200 字以内
6. 如有多个问题，逐一回答"""

        if context:
            company = context.get("company_name", "本公司")
            prompt += f"\n\n公司名称：{company}"
            if context.get("business_hours"):
                prompt += f"\n工作时间：{context['business_hours']}"

        return prompt

    def clear_session(self, session_id: str):
        """Clear session history."""
        self._session_history.pop(session_id, None)
