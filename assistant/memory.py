"""
Persistent Memory System
Categories: personal, conversation, tasks, preferences
User has full control: view / edit / delete / clear.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    select,
    delete,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


class MemoryEntry(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True)  # personal | conversation | task | preference
    key = Column(String(200), nullable=True, index=True)
    value = Column(Text, nullable=False)
    meta = Column(Text, nullable=True)  # JSON extra data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationMessage(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="pending")  # pending | completed | cancelled
    priority = Column(Integer, default=0)
    deadline = Column(DateTime, nullable=True)
    reminder_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MemoryManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def _session(self) -> Session:
        return self.SessionLocal()

    # ── Generic memory ───────────────────────────────────
    def set(self, category: str, key: str, value: str, meta: Optional[Dict] = None) -> int:
        with self._session() as s:
            existing = s.execute(
                select(MemoryEntry).where(
                    MemoryEntry.category == category,
                    MemoryEntry.key == key,
                )
            ).scalar_one_or_none()
            if existing:
                existing.value = value
                existing.meta = json.dumps(meta) if meta else None
                existing.updated_at = datetime.utcnow()
                s.commit()
                return existing.id
            entry = MemoryEntry(
                category=category,
                key=key,
                value=value,
                meta=json.dumps(meta) if meta else None,
            )
            s.add(entry)
            s.commit()
            s.refresh(entry)
            return entry.id

    def get(self, category: str, key: str) -> Optional[str]:
        with self._session() as s:
            entry = s.execute(
                select(MemoryEntry).where(
                    MemoryEntry.category == category,
                    MemoryEntry.key == key,
                )
            ).scalar_one_or_none()
            return entry.value if entry else None

    def list_by_category(self, category: str) -> List[Dict[str, Any]]:
        with self._session() as s:
            rows = s.execute(
                select(MemoryEntry).where(MemoryEntry.category == category)
            ).scalars().all()
            return [
                {
                    "id": r.id,
                    "key": r.key,
                    "value": r.value,
                    "meta": json.loads(r.meta) if r.meta else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]

    def delete(self, entry_id: int) -> bool:
        with self._session() as s:
            result = s.execute(delete(MemoryEntry).where(MemoryEntry.id == entry_id))
            s.commit()
            return result.rowcount > 0

    def clear_category(self, category: str) -> int:
        with self._session() as s:
            result = s.execute(delete(MemoryEntry).where(MemoryEntry.category == category))
            s.commit()
            return result.rowcount

    def clear_all(self) -> None:
        with self._session() as s:
            s.execute(delete(MemoryEntry))
            s.execute(delete(ConversationMessage))
            s.execute(delete(Task))
            s.commit()

    # ── Conversation history ─────────────────────────────
    def add_message(self, role: str, content: str) -> int:
        with self._session() as s:
            msg = ConversationMessage(role=role, content=content)
            s.add(msg)
            s.commit()
            s.refresh(msg)
            return msg.id

    def get_recent_messages(self, limit: int = 20) -> List[Dict[str, str]]:
        with self._session() as s:
            rows = (
                s.execute(
                    select(ConversationMessage)
                    .order_by(ConversationMessage.id.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            # reverse to chronological order
            return [{"role": r.role, "content": r.content} for r in reversed(rows)]

    def clear_conversation(self) -> None:
        with self._session() as s:
            s.execute(delete(ConversationMessage))
            s.commit()

    # ── Tasks ────────────────────────────────────────────
    def create_task(
        self,
        title: str,
        description: str = "",
        priority: int = 0,
        deadline: Optional[datetime] = None,
        reminder_at: Optional[datetime] = None,
    ) -> int:
        with self._session() as s:
            task = Task(
                title=title,
                description=description,
                priority=priority,
                deadline=deadline,
                reminder_at=reminder_at,
            )
            s.add(task)
            s.commit()
            s.refresh(task)
            return task.id

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._session() as s:
            q = select(Task)
            if status:
                q = q.where(Task.status == status)
            rows = s.execute(q.order_by(Task.priority.desc(), Task.deadline)).scalars().all()
            return [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "reminder_at": t.reminder_at.isoformat() if t.reminder_at else None,
                }
                for t in rows
            ]

    def complete_task(self, task_id: int) -> bool:
        with self._session() as s:
            task = s.get(Task, task_id)
            if not task:
                return False
            task.status = "completed"
            task.updated_at = datetime.utcnow()
            s.commit()
            return True

    def uncomplete_task(self, task_id: int) -> bool:
        with self._session() as s:
            task = s.get(Task, task_id)
            if not task:
                return False
            task.status = "pending"
            task.updated_at = datetime.utcnow()
            s.commit()
            return True


    def delete_task(self, task_id: int) -> bool:
        with self._session() as s:
            result = s.execute(delete(Task).where(Task.id == task_id))
            s.commit()
            return result.rowcount > 0

    # ── User context helper for the brain ────────────────
    def get_user_context_summary(self) -> str:
        parts = []
        personal = self.list_by_category("personal")
        if personal:
            parts.append("Personal info:")
            for p in personal:
                parts.append(f"  - {p['key']}: {p['value']}")
        prefs = self.list_by_category("preference")
        if prefs:
            parts.append("Preferences:")
            for p in prefs:
                parts.append(f"  - {p['key']}: {p['value']}")
        pending = self.list_tasks(status="pending")
        if pending:
            parts.append("Pending tasks:")
            for t in pending[:5]:
                parts.append(f"  - {t['title']}")
        return "\n".join(parts) if parts else ""
