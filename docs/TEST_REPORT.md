# Test Report

## T-2026-00055: WeCom AI客服 — Dify Agent 引擎 + RAG 知识库

| 字段 | 值 |
|------|-----|
| Task ID | T-2026-00055 |
| Project | P-2026-00012 (WeCom AI Customer Service) |
| 分支 | feat/T-2026-00055-wecom-ai-engine |
| 测试日期 | 2026-05-28 |
| 测试环境 | Python 3.12.3 / pytest 9.0.3 |
| 测试命令 | `python3 -m pytest tests/test_engine.py -v` |

---

## 测试概要

| Case-ID | 描述 | 结果 | 备注 |
|---------|------|------|------|
| TC-001 | 意图识别 — 产品咨询 | ✅ PASS | |
| TC-002 | 意图识别 — 订单查询 | ✅ PASS | |
| TC-003 | 意图识别 — 售后支持 | ✅ PASS | |
| TC-004 | 意图识别 — 价格咨询 | ✅ PASS | |
| TC-005 | 意图识别 — 投诉 | ✅ PASS | |
| TC-006 | 意图识别 — 转人工 | ✅ PASS | |
| TC-007 | 意图识别 — 技术支持 | ✅ PASS | |
| TC-008 | 意图识别 — 退款/换货 | ✅ PASS | |
| TC-009 | 意图识别 — 通用聊天 | ✅ PASS | |
| TC-010 | 意图识别 — 多意图检测 | ✅ PASS | |
| TC-011 | 升级判断 — 投诉 | ✅ PASS | |
| TC-012 | 升级判断 — 转人工 | ✅ PASS | |
| TC-013 | 升级判断 — 普通意图 | ✅ PASS | |
| TC-014 | 意图置信度阈值 | ✅ PASS | |
| TC-015 | 知识库 — 添加文档 | ✅ PASS | |
| TC-016 | 知识库 — 按查询搜索 | ✅ PASS | |
| TC-017 | 知识库 — 分数排序 | ✅ PASS | |
| TC-018 | 知识库 — 无结果 | ✅ PASS | |
| TC-019 | 知识库 — 返回 KnowledgeResult | ✅ PASS | |
| TC-020 | 知识库 — 无匹配返回 None | ✅ PASS | |
| TC-021 | 知识库 — top_k 限制 | ✅ PASS | |
| TC-022 | 知识库 — 元数据保留 | ✅ PASS | |
| TC-023 | 知识库 — 空库 size=0 | ✅ PASS | |
| TC-024 | SOP — 退款规则匹配 | ✅ PASS | |
| TC-025 | SOP — 投诉规则匹配 | ✅ PASS | |
| TC-026 | SOP — 无匹配 | ✅ PASS | |
| TC-027 | SOP — 错误意图不匹配 | ✅ PASS | |
| TC-028 | SOP — 规则属性 | ✅ PASS | |
| TC-029 | LLM — 模拟回复 | ✅ PASS | |
| TC-030 | LLM — 调用计数 | ✅ PASS | |
| TC-031 | LLM — API Key 配置 | ✅ PASS | |
| TC-032 | Agent — SOP 触发 | ✅ PASS | |
| TC-033 | Agent — 升级转人工 | ✅ PASS | |
| TC-034 | Agent — 转人工请求 | ✅ PASS | |
| TC-035 | Agent — 返回回复 | ✅ PASS | |
| TC-036 | Agent — 知识库匹配 | ✅ PASS | |
| TC-037 | Agent — 处理时间跟踪 | ✅ PASS | |
| TC-038 | Agent — 会话历史 | ✅ PASS | |
| TC-039 | Agent — 清除会话 | ✅ PASS | |
| TC-040 | Agent — 客户上下文 | ✅ PASS | |

## 结果

- **总计**: 40/40 PASS (100%)
- **通过标准**: 全部 PASS ✅

## 交付清单

| 文件 | 说明 |
|------|------|
| `engine/app.py` | AI 客服核心引擎（意图识别 + 知识库 + SOP + LLM + Agent） |
| `engine/__init__.py` | 包初始化 |
| `tests/test_engine.py` | 40 条单元测试 |

## 核心功能

### IntentRecognizer
- 关键词匹配 9 种意图（产品/订单/售后/退款/技术/价格/投诉/人工/通用）
- 多意图检测
- 自动升级判断（投诉 + 转人工 → 转人工客服）

### KnowledgeBase
- 文档添加（支持标题、内容、元数据）
- 中文 n-gram 搜索 + 英文分词搜索
- top_k 结果截断
- 标题匹配加权

### SOPEngine
- 规则匹配（意图触发 + 关键词匹配）
- 回复模板 + 后续动作

### CustomerServiceAgent
- 完整处理流程：意图识别 → 升级检查 → SOP 匹配 → 知识库查询 → LLM 兜底
- 会话历史管理
- 处理时间跟踪
