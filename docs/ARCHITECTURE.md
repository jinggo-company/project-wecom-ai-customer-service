# ARCHITECTURE — 企业微信 AI 自动客服与私域运营工具

## 项目信息

| 字段 | 值 |
|------|------|
| 项目 ID | P-2026-00012 |
| 关联任务 | T-2026-00045 |

---

## 1. 系统总览

```
┌──────────────┐      Webhook / API       ┌───────────────────────┐
│   企业微信    │◄───────────────────────►│    WeCom 网关服务       │
│  (员工/客户)  │                          │  Flask + 事件解析       │
└──────────────┘                          └──────────┬────────────┘
                                                     │
                    ┌────────────────────────────────┼────────────────┐
                    ▼                                ▼                ▼
            ┌───────────────┐              ┌──────────────┐   ┌──────────────┐
            │   AI 客服引擎  │              │  SOP 运营引擎 │   │  数据看板     │
            │  Dify + RAG   │              │  Celery Beat │   │  React+ECharts│
            └───────┬───────┘              └──────┬───────┘   └──────────────┘
                    │                              │
                    └──────────────┬───────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │      数据存储层                │
                    │  PostgreSQL + Redis + Milvus │
                    └──────────────────────────────┘
```

## 2. 模块划分

### 2.1 项目目录结构

```
wecom-ai-cs/
├── gateway/                    # 企微网关服务
│   ├── app.py                  # Flask 应用入口
│   ├── webhook/                # 回调处理
│   │   ├── message.py          # 消息回调（文本/图片/语音/文件）
│   │   ├── event.py            # 事件回调（成员变更/入群/退群）
│   │   └── media.py            # 媒体文件回调
│   ├── api/                    # 企微 API 封装
│   │   ├── contact.py          # 通讯录 API
│   │   ├── message.py          # 消息发送 API
│   │   ├── group.py            # 群管理 API
│   │   ├── chatarchive.py      # 会话存档 API
│   │   └── auth.py             # 鉴权（access_token 管理）
│   └── config.py               # 配置
├── agent/                      # AI 客服引擎
│   ├── dify/                   # Dify 配置
│   │   ├── app.yaml            # Dify Agent 定义
│   │   ├── knowledge_base.yaml # 知识库配置
│   │   └── tools.yaml          # 自定义工具定义
│   ├── intent/                 # 意图识别
│   │   ├── classifier.py       # 意图分类器
│   │   └── templates.py        # 意图-回复模板映射
│   ├── rag/                    # RAG 检索
│   │   ├── retriever.py        # 向量检索
│   │   ├── indexer.py          # 知识库索引构建
│   │   └── chunker.py          # 文本分块策略
│   └── response/               # 回复生成
│       ├── generator.py        # LLM 回复生成
│       ├── fallback.py         # 降级策略（模板/转人工）
│       └── filter.py           # 安全过滤（敏感词/合规）
├── sop/                        # SOP 自动化引擎
│   ├── engine.py               # SOP 引擎核心
│   ├── rules/                  # SOP 规则定义
│   │   ├── welcome.py          # 欢迎 SOP
│   │   ├── followup.py         # 跟进 SOP
│   │   ├── tag.py              # 标签 SOP
│   │   └── campaign.py         # 营销活动 SOP
│   ├── scheduler.py            # 定时任务调度（Celery Beat）
│   └── executor.py             # SOP 执行器
├── tags/                       # 用户标签系统
│   ├── manager.py              # 标签管理器
│   ├── rules.py                # 标签规则引擎
│   └── segment.py              # 用户分群
├── dashboard/                  # 数据看板前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Overview.tsx    # 总览页
│   │   │   ├── Session.tsx     # 会话分析
│   │   │   ├── Tags.tsx        # 标签分析
│   │   │   └── SOP.tsx         # SOP 执行分析
│   │   ├── components/
│   │   └── App.tsx
│   └── package.json
├── backend/                    # 后端 API 服务
│   ├── app.py                  # FastAPI 入口
│   ├── routes/
│   │   ├── users.py            # 用户管理
│   │   ├── sessions.py         # 会话管理
│   │   ├── tags.py             # 标签管理
│   │   ├── sop.py              # SOP 管理
│   │   └── analytics.py        # 数据分析
│   ├── services/
│   │   ├── user_service.py     # 用户业务逻辑
│   │   ├── session_service.py  # 会话业务逻辑
│   │   └── analytics_service.py # 统计逻辑
│   └── db/
│       ├── models.py           # SQLAlchemy 数据模型
│       └── engine.py           # DB 连接
├── deploy/                     # 部署配置
│   ├── docker-compose.yml
│   ├── Dockerfile.*
│   └── nginx.conf
└── tests/
```

### 2.2 企微对接架构

```
企微服务器
    │
    ├── 消息回调 ──► [Webhook Flask] ──► 事件解析 ──► 消息分发
    │                                            │
    │                                            ├──► AI 客服引擎（自动回复）
    │                                            ├──► SOP 引擎（自动化流程）
    │                                            └──► 会话存档（异步写入 DB）
    │
    ├── 主动调用 ──► [企微 API 封装] ──► access_token ──► HTTP 请求
    │
    └── 会话存档 ──► [独立拉取服务] ──► 解密 ──► 写入 DB
```

### 2.3 意图识别与回复流程

```
用户消息
    │
    ▼
[消息预处理] ──去噪/分词/语言检测──► [意图分类]
                                         │
    ┌────────────────────────────────────┼────────────────────────────────────┐
    ▼                                    ▼                                    ▼
[知识库问答意图]                  [客服工单意图]                      [闲聊/其他意图]
    │                                    │                                    │
    ▼                                    ▼                                    ▼
[RAG 检索] ──► [LLM 生成回复]     [转人工] ──► [工单队列]           [模板回复/默认回复]
    │                                    │
    ▼                                    ▼
[安全过滤] ──► [发送回复]          [通知客服] ──► [客服回复]
```

## 3. 数据模型

```python
# SQLAlchemy 核心模型

class WeComUser(Base):
    """企微用户（客户）"""
    id = Column(String, primary_key=True)       # 企微外部联系人 ID
    name = Column(String)
    phone = Column(String)
    tags = Column(JSON)                          # 标签列表
    added_by = Column(String)                    # 添加人员工 ID
    added_time = Column(DateTime)
    last_message_time = Column(DateTime)
    session_count = Column(Integer, default=0)

class WeComStaff(Base):
    """企微员工"""
    id = Column(String, primary_key=True)       # 企微用户 ID
    name = Column(String)
    department = Column(String)
    role = Column(String)                        # admin / agent_operator / viewer

class Session(Base):
    """会话记录"""
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('wecom_user.id'))
    staff_id = Column(String)
    channel = Column(String)                     # single / group
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    message_count = Column(Integer)
    ai_handled = Column(Boolean)                 # AI 处理的条数
    human_handled = Column(Boolean)              # 人工介入
    resolution_status = Column(String)           # resolved / pending / transferred

class Message(Base):
    """消息记录"""
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('session.id'))
    sender_id = Column(String)
    sender_type = Column(String)                 # customer / staff / ai
    content = Column(Text)
    msg_type = Column(String)                    # text / image / voice / file
    timestamp = Column(DateTime)
    intent = Column(String)                      # AI 意图识别结果

class SOP(Base):
    """SOP 规则定义"""
    id = Column(String, primary_key=True)
    name = Column(String)
    trigger_type = Column(String)                # time / event / condition
    trigger_config = Column(JSON)                # 触发条件配置
    actions = Column(JSON)                       # 执行动作列表
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime)

class SOPExecution(Base):
    """SOP 执行记录"""
    id = Column(String, primary_key=True)
    sop_id = Column(String, ForeignKey('sop.id'))
    target_user_id = Column(String)
    status = Column(String)                      # pending / running / success / failed
    executed_at = Column(DateTime)
    result = Column(JSON)

class Tag(Base):
    """标签定义"""
    id = Column(String, primary_key=True)
    name = Column(String)
    category = Column(String)                    # 行业 / 行为 / 自动 / 手动
    rule = Column(JSON)                          # 自动打标规则
    user_count = Column(Integer, default=0)
```

## 4. AI 客服引擎详细设计

### 4.1 Dify Agent 配置

```yaml
# dify/app.yaml
app:
  name: "WeCom AI Customer Service"
  mode: "agent-chat"
  model:
    provider: "tongyi"
    name: "qwen-max"
    mode: "chat"
  
knowledge_base:
  indexing_technique: "high_quality"
  retrieval_model:
    top_k: 5
    score_threshold: 0.7
    
tools:
  - type: "builtin"
    name: "google_search"
  - type: "custom"
    name: "wecom_send_message"
    api: "/api/agent/tools/wecom/send"
  - type: "custom"
    name: "query_order"
    api: "/api/agent/tools/order/query"
    
workflow:
  nodes:
    - id: "start"
      type: "start"
    - id: "intent_classifier"
      type: "llm"
      prompt: "判断用户意图分类: [product_inquiry, after_sales, order_query, complaint, chitchat, escalate]"
    - id: "rag_retriever"
      type: "knowledge_retrieval"
      condition: "intent in [product_inquiry, after_sales]"
    - id: "response_generator"
      type: "llm"
      prompt: "根据检索结果生成回复"
    - id: "order_query"
      type: "tool_call"
      condition: "intent == order_query"
    - id: "escalate"
      type: "end"
      condition: "intent in [complaint, escalate]"
      output: "TRANSFER_TO_HUMAN"
```

### 4.2 RAG 检索管线

```
文档入库
    │
    ▼
[文本提取] ──► [文本分块] ──► [向量化(BGE-m3)] ──► [写入 Milvus]
                                    │
                                    ▼
                              [构建倒排索引]

用户查询
    │
    ▼
[查询向量化] ──► [混合检索 (向量 + BM25)] ──► [重排序] ──► [Top-5 结果]
```

## 5. SOP 引擎详细设计

### 5.1 SOP 触发类型

| 类型 | 触发条件 | 示例 |
|------|----------|------|
| 时间触发 | 固定时间点 / 周期 | 每天早上 9:00 发送早安问候 |
| 事件触发 | 用户行为事件 | 用户首次添加 → 发送欢迎语 |
| 条件触发 | 满足标签/属性条件 | 用户标签含 "高价值" → 推送专属优惠 |

### 5.2 SOP 规则引擎

```
触发事件
    │
    ▼
[规则匹配] ──条件评估──► [是否执行?]
                            │
                      ┌─────┴─────┐
                      ▼           ▼
                  [执行动作]    [跳过]
                      │
                      ▼
              [动作序列执行]
              1. 发送消息
              2. 打标签
              3. 记录日志
              4. 通知员工
```

### 5.3 典型 SOP 示例

```yaml
# sop/rules/welcome.yaml
sop_id: "SOP-WELCOME-001"
name: "新客户欢迎流程"
trigger:
  type: "event"
  event: "customer_added"
actions:
  - type: "send_message"
    delay: "0s"
    template: "welcome_v1"
  - type: "add_tag"
    delay: "5s"
    tags: ["新客户"]
  - type: "notify_staff"
    delay: "10s"
    message: "新客户 {{customer_name}} 已添加，请及时跟进"
  - type: "send_message"
    delay: "86400s"  # 24小时后
    template: "followup_day1_v1"
    condition: "session_count <= 1"
  - type: "send_message"
    delay: "259200s"  # 3天后
    template: "followup_day3_v1"
    condition: "session_count <= 2"
```

## 6. 数据看板架构

```
┌─────────────────────────────────────────┐
│              数据看板 (React)             │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │ 总览页  │ │会话分析 │ │ 标签分析  │ │
│  └─────────┘ └─────────┘ └───────────┘ │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │SOP 分析 │ │ 效果报告 │ │ 实时告警  │ │
│  └─────────┘ └─────────┘ └───────────┘ │
└───────────────┬─────────────────────────┘
                │ REST API
                ▼
┌─────────────────────────────────────────┐
│          后端 API (FastAPI)               │
│  GET /api/analytics/overview            │
│  GET /api/analytics/sessions            │
│  GET /api/analytics/tags                │
│  GET /api/analytics/sop                 │
│  GET /api/analytics/realtime            │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│          PostgreSQL + Redis               │
│  (预计算视图 + 实时缓存)                   │
└─────────────────────────────────────────┘
```

## 7. 接口清单

### 7.1 内部 API

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 会话列表 | GET | /api/sessions | 分页查询会话 |
| 会话详情 | GET | /api/sessions/:id | 查看会话消息记录 |
| 用户列表 | GET | /api/users | 客户列表 + 标签 |
| 用户标签 | PUT | /api/users/:id/tags | 修改用户标签 |
| SOP 列表 | GET | /api/sops | SOP 规则列表 |
| SOP 创建 | POST | /api/sops | 创建 SOP 规则 |
| SOP 执行 | POST | /api/sops/:id/execute | 手动触发 SOP |
| 数据看板 | GET | /api/analytics/* | 各维度统计 |

### 7.2 Agent 工具 API

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 企微发消息 | POST | /api/agent/tools/wecom/send | 调用企微 API 发消息 |
| 查询订单 | GET | /api/agent/tools/order/query | 查询客户订单状态 |
| 查询知识库 | POST | /api/agent/tools/kb/query | RAG 检索知识库 |

## 8. Docker 部署架构

```yaml
# docker-compose.yml (概要)
services:
  gateway:
    image: wecom-gateway:latest
    ports: ["5000:5000"]
    depends_on: [redis, backend]
  
  backend:
    image: wecom-backend:latest
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
  
  agent:
    image: dify:latest
    ports: ["3000:3000"]
    depends_on: [milvus, postgres]
  
  celery_worker:
    image: wecom-backend:latest
    command: celery -A sop worker
    depends_on: [redis, backend]
  
  celery_beat:
    image: wecom-backend:latest
    command: celery -A sop beat
    depends_on: [redis]
  
  postgres:
    image: postgres:16
  
  redis:
    image: redis:7
  
  milvus:
    image: milvusdb/milvus:v2.4
  
  dashboard:
    image: wecom-dashboard:latest
    ports: ["3001:80"]
```

## 9. 安全设计

| 威胁 | 防护措施 |
|------|----------|
| 企微 Token 泄露 | Token 加密存储 + 自动刷新 + 最小权限 |
| 会话存档合规 | 数据脱敏 + 访问审计 + 加密存储 |
| AI 回复安全 | 敏感词过滤 + 人工审核开关 + 回复模板兜底 |
| 用户隐私保护 | GDPR/个保法合规 + 数据最小化 + 可删除请求 |
| API 鉴权 | JWT + RBAC（admin/operator/viewer） |
| 频率限制 | Redis 滑动窗口限流 |
