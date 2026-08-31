"""Safety contract for the optional Memvid cold-archive adapter."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from aura_backend import aura_real_memvid


class _FakeArchive:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def put(self, **entry: Any) -> None:
        self.entries.append(entry)

    def close(self) -> None:
        return None


class _ConversationCollection:
    def __init__(self) -> None:
        self.deleted_ids: list[str] = []
        old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()
        self._documents = [
            "sanitized archived conversation",
            "another user's sanitized conversation",
        ]
        self._metadatas = [
            {
                "user_id": "local-user",
                "timestamp": old_timestamp,
                "emotion_name": "calm",
                "brainwave": "alpha",
            },
            {
                "user_id": "different-user",
                "timestamp": old_timestamp,
                "emotion_name": "calm",
                "brainwave": "alpha",
            },
        ]

    def get(self, *, include: list[str]) -> dict[str, Any]:
        if include:
            return {
                "documents": self._documents,
                "metadatas": self._metadatas,
            }
        return {"ids": ["conversation-1", "conversation-2"]}

    def delete(self, *, ids: list[str]) -> None:
        self.deleted_ids.extend(ids)


def test_archiving_never_deletes_the_active_source(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Creating a cold archive is copy-only until restore parity is verified."""
    archive = _FakeArchive()
    conversations = _ConversationCollection()
    adapter = aura_real_memvid.AuraRealMemvid.__new__(
        aura_real_memvid.AuraRealMemvid
    )
    adapter.active_memory_days = 30
    adapter.memvid_video_path = tmp_path
    adapter.embedding_model = "local-test-embedding"
    adapter.conversations = conversations
    adapter.video_archives = {}

    monkeypatch.setattr(aura_real_memvid, "REAL_MEMVID_AVAILABLE", True)
    monkeypatch.setattr(
        aura_real_memvid.memvid_sdk,
        "create",
        lambda *_args, **_kwargs: archive,
    )
    monkeypatch.setattr(
        aura_real_memvid.memvid_sdk,
        "use",
        lambda *_args, **_kwargs: archive,
    )

    result = adapter.archive_conversations_to_video(user_id="local-user")

    assert result["archived_count"] == 1
    assert result["source_records_retained"] is True
    assert result["deletion_performed"] is False
    assert len(archive.entries) == 1
    assert archive.entries[0]["metadata"]["user_id"] == "local-user"
    assert conversations.deleted_ids == []
