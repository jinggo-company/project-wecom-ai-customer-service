"""
Backend API Service — FastAPI entry point
T-2026-00056 | P-2026-00012

Provides REST API for: users, sessions, tags, SOP, analytics
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional
import uuid

app = FastAPI(
    title="WeCom AI Customer Service API",
    version="1.0.0",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory stores (replaced by DB in production) ─────────
_sessions_store: dict = {}
_users_store: dict = {}
_analytics_cache: dict = {}

# ── Mock data ─────────────────────────────────────────────────
def _seed_mock_data():
    if not _sessions_store:
        now = datetime.utcnow()
        for i in range(50):
            sid = str(uuid.uuid4())[:8]
            _sessions_store[sid] = {
                "id": sid,
                "user_id": f"user_{i % 20:03d}",
                "staff_id": f"staff_{i % 3:02d}",
                "channel": "single" if i % 5 != 0 else "group",
                "start_time": (now - timedelta(hours=i)).isoformat(),
                "message_count": 3 + (i % 10),
                "ai_handled": i % 3 != 0,
                "human_handled": i % 3 == 0,
                "resolution_status": "resolved" if i % 4 != 0 else "pending",
                "intent": ["product_inquiry", "order_query", "after_sales", "complaint", "general_chat"][i % 5],
            }
    if not _users_store:
        for i in range(20):
            uid = f"user_{i:03d}"
            _users_store[uid] = {
                "id": uid,
                "name": f"客户{i}",
                "tags": ["新客户", "活跃用户"] if i % 3 == 0 else ["普通"],
                "session_count": 1 + (i % 8),
                "added_time": (datetime.utcnow() - timedelta(days=i)).isoformat(),
            }

_seed_mock_data()

# ── Analytics ───────────────────────────────────────────────

@app.get("/api/analytics/overview")
def get_overview():
    """Overview stats: today's messages, AI/human split, resolution rate"""
    total_sessions = len(_sessions_store)
    ai_handled = sum(1 for s in _sessions_store.values() if s["ai_handled"])
    human_handled = sum(1 for s in _sessions_store.values() if s["human_handled"])
    resolved = sum(1 for s in _sessions_store.values() if s["resolution_status"] == "resolved")

    # Mock real-time data
    return {
        "total_sessions": total_sessions,
        "total_messages": sum(s["message_count"] for s in _sessions_store.values()),
        "ai_handled": ai_handled,
        "human_handled": human_handled,
        "transfer_to_human_rate": round(human_handled / max(total_sessions, 1) * 100, 1),
        "resolution_rate": round(resolved / max(total_sessions, 1) * 100, 1),
        "total_users": len(_users_store),
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/api/analytics/sessions")
def get_session_analytics(
    period: str = Query("day", enum=["day", "week", "month"]),
    group_by: str = Query("hour", enum=["hour", "day"]),
):
    """Session analytics: messages over time"""
    now = datetime.utcnow()
    data = []
    if group_by == "hour":
        for i in range(24):
            data.append({
                "time": f"{i:02d}:00",
                "sessions": 5 + (i % 8) * 2,
                "messages": 15 + (i % 10) * 5,
                "ai_ratio": round(0.6 + (i % 4) * 0.05, 2),
            })
    elif group_by == "day":
        for i in range(7):
            data.append({
                "time": f"Day {i+1}",
                "sessions": 30 + i * 5,
                "messages": 120 + i * 20,
                "ai_ratio": round(0.65 + i * 0.02, 2),
            })
    return {"period": period, "data": data}

@app.get("/api/analytics/intents")
def get_intent_distribution():
    """Intent distribution chart data"""
    intents = {}
    for s in _sessions_store.values():
        intent = s.get("intent", "unknown")
        intents[intent] = intents.get(intent, 0) + 1
    return {
        "data": [
            {"name": name, "value": count}
            for name, count in sorted(intents.items(), key=lambda x: -x[1])
        ]
    }

@app.get("/api/analytics/tags")
def get_tag_analytics():
    """Tag coverage analysis"""
    tag_counts = {}
    for u in _users_store.values():
        for tag in u.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    total_users = len(_users_store)
    tagged = sum(1 for u in _users_store.values() if u.get("tags"))

    return {
        "tag_coverage_rate": round(tagged / max(total_users, 1) * 100, 1),
        "total_users": total_users,
        "tagged_users": tagged,
        "tags": sorted(
            [{"name": name, "count": count} for name, count in tag_counts.items()],
            key=lambda x: -x["count"],
        ),
    }

@app.get("/api/analytics/sop")
def get_sop_analytics():
    """SOP execution analytics"""
    return {
        "total_rules": 4,
        "enabled_rules": 4,
        "total_executions": 128,
        "successful_executions": 120,
        "failed_executions": 8,
        "success_rate": 93.8,
        "executions_by_rule": [
            {"rule": "新客户欢迎流程", "count": 50, "success_rate": 100.0},
            {"rule": "客户定期跟进", "count": 45, "success_rate": 91.1},
            {"rule": "自动标签打标", "count": 25, "success_rate": 96.0},
            {"rule": "营销活动精准触达", "count": 8, "success_rate": 87.5},
        ],
    }

@app.get("/api/analytics/user_growth")
def get_user_growth():
    """User growth chart data"""
    data = []
    for i in range(30):
        data.append({
            "date": f"Day {i+1}",
            "new_users": 3 + (i % 5),
            "total_users": 20 + i * 2 + (i % 3),
        })
    return {"data": data}

@app.get("/api/analytics/realtime")
def get_realtime():
    """Real-time metrics (simulated)"""
    now = datetime.utcnow()
    return {
        "active_sessions": 12,
        "queue_length": 3,
        "avg_response_time_ms": 2340,
        "ai_accuracy_rate": 87.5,
        "timestamp": now.isoformat(),
    }

# ── Sessions ────────────────────────────────────────────────

@app.get("/api/sessions")
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    channel: Optional[str] = None,
):
    """List sessions with pagination and filters"""
    sessions = list(_sessions_store.values())
    if status:
        sessions = [s for s in sessions if s["resolution_status"] == status]
    if channel:
        sessions = [s for s in sessions if s["channel"] == channel]

    total = len(sessions)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": sessions[start:end],
    }

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """Get session detail"""
    session = _sessions_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

# ── Users ───────────────────────────────────────────────────

@app.get("/api/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List users"""
    users = list(_users_store.values())
    total = len(users)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": users[start:end],
    }

@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    user = _users_store.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/api/users/{user_id}/tags")
def update_user_tags(user_id: str, tags: list[str]):
    if user_id not in _users_store:
        raise HTTPException(status_code=404, detail="User not found")
    _users_store[user_id]["tags"] = tags
    return {"user_id": user_id, "tags": tags}

# ── Health ──────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
