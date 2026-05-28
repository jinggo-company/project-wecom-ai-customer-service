"""
Tag Manager — user tagging, rule-based auto-tagging, segmentation
T-2026-00056 | P-2026-00012
"""
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Tag:
    """标签定义"""
    id: str
    name: str
    category: str  # industry / behavior / auto / manual
    rule: dict = field(default_factory=dict)
    user_count: int = 0
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.created_at:
            d["created_at"] = self.created_at.isoformat()
        return d


class TagManager:
    """用户标签管理器"""

    def __init__(self):
        self._tags: dict[str, Tag] = {}
        self._user_tags: dict[str, set] = {}  # user_id -> set of tag_ids
        self._tag_users: dict[str, set] = {}  # tag_id -> set of user_ids

    def add_tag(self, tag: Tag):
        self._tags[tag.id] = tag
        if tag.id not in self._tag_users:
            self._tag_users[tag.id] = set()
        logger.info(f"Tag added: {tag.id} — {tag.name}")

    def remove_tag(self, tag_id: str) -> bool:
        if tag_id in self._tags:
            del self._tags[tag_id]
            # Remove from all users
            for user_id in self._tag_users.get(tag_id, set()):
                self._user_tags.get(user_id, set()).discard(tag_id)
            self._tag_users.pop(tag_id, None)
            return True
        return False

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        return self._tags.get(tag_id)

    def list_tags(self, category: str = None) -> list[Tag]:
        tags = list(self._tags.values())
        if category:
            tags = [t for t in tags if t.category == category]
        return tags

    def add_tag_to_user(self, user_id: str, tag_id: str) -> bool:
        tag = self._tags.get(tag_id)
        if not tag:
            return False
        if user_id not in self._user_tags:
            self._user_tags[user_id] = set()
        if tag_id not in self._tag_users:
            self._tag_users[tag_id] = set()

        self._user_tags[user_id].add(tag_id)
        self._tag_users[tag_id].add(user_id)
        tag.user_count = len(self._tag_users[tag_id])
        return True

    def remove_tag_from_user(self, user_id: str, tag_id: str) -> bool:
        if user_id in self._user_tags and tag_id in self._user_tags[user_id]:
            self._user_tags[user_id].discard(tag_id)
            self._tag_users.get(tag_id, set()).discard(user_id)
            tag = self._tags.get(tag_id)
            if tag:
                tag.user_count = len(self._tag_users.get(tag_id, set()))
            return True
        return False

    def get_user_tags(self, user_id: str) -> list[Tag]:
        tag_ids = self._user_tags.get(user_id, set())
        return [self._tags[tid] for tid in tag_ids if tid in self._tags]

    def get_users_by_tag(self, tag_id: str) -> set:
        return self._tag_users.get(tag_id, set())

    def get_users_with_all_tags(self, tag_ids: list[str]) -> set:
        if not tag_ids:
            return set()
        result = self._tag_users.get(tag_ids[0], set()).copy()
        for tid in tag_ids[1:]:
            result &= self._tag_users.get(tid, set())
        return result

    def apply_auto_rules(self, user_id: str, user_attrs: dict) -> list[str]:
        """Apply auto-tagging rules based on user attributes."""
        applied = []
        for tag in self._tags.values():
            if tag.category != "auto":
                continue
            rule = tag.rule
            if not rule:
                continue

            match = True
            for key, value in rule.items():
                if user_attrs.get(key) != value:
                    match = False
                    break

            if match:
                self.add_tag_to_user(user_id, tag.id)
                applied.append(tag.id)

        return applied

    def get_segment(self, tag_ids: list[str]) -> dict:
        """Get user segment by tag combination."""
        user_ids = self.get_users_with_all_tags(tag_ids)
        tags_info = []
        for tid in tag_ids:
            tag = self._tags.get(tid)
            if tag:
                tags_info.append(tag.to_dict())
        return {
            "tags": tags_info,
            "user_count": len(user_ids),
            "user_ids": list(user_ids),
        }

    def get_stats(self) -> dict:
        return {
            "total_tags": len(self._tags),
            "tagged_users": len([u for u, t in self._user_tags.items() if t]),
            "total_tag_assignments": sum(len(t) for t in self._user_tags.values()),
            "tags": {tid: t.to_dict() for tid, t in self._tags.items()},
        }
