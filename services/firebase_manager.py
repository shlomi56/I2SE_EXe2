"""Firebase Realtime Database access layer.

`get_firebase_app()` initialises the Firebase Admin SDK exactly once per server
process (singleton). `CloudPoolManager` is the only class that reads/writes the
database: comments (F2), polls (F3) and the anonymous homework Cloud Pool (F5).

Database schema:
    /comments/{pushId}     : {text, author, ts}
    /polls/active_id       : "<pollId>" | null
    /polls/items/{pollId}  : {question, options[], counts[], created_at, closed}
    /submissions/{pushId}  : {code, language, ts}
"""
from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, List, Optional

import firebase_admin
import streamlit as st
from firebase_admin import credentials, db


class FirebaseConfigError(RuntimeError):
    """Raised when Firebase credentials / database URL are missing or invalid."""


def firebase_is_configured() -> bool:
    has_creds = bool(os.getenv("FIREBASE_CREDENTIALS_PATH") or os.getenv("FIREBASE_CREDENTIALS_JSON"))
    return has_creds and bool(os.getenv("FIREBASE_DATABASE_URL"))


def _load_credentials() -> credentials.Certificate:
    raw_json = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
    if raw_json:
        try:
            return credentials.Certificate(json.loads(raw_json))
        except (ValueError, TypeError) as exc:
            raise FirebaseConfigError(f"FIREBASE_CREDENTIALS_JSON is not valid JSON: {exc}") from exc

    path = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
    if path:
        if not os.path.isfile(path):
            raise FirebaseConfigError(f"Firebase credentials file not found: {path}")
        return credentials.Certificate(path)

    raise FirebaseConfigError(
        "Set FIREBASE_CREDENTIALS_PATH (service-account JSON file) or "
        "FIREBASE_CREDENTIALS_JSON (raw JSON string) in your .env file."
    )


@st.cache_resource(show_spinner=False)
def get_firebase_app() -> firebase_admin.App:
    """Singleton Firebase app (cached across Streamlit reruns and sessions)."""
    if firebase_admin._apps:  # already initialised in this process
        return firebase_admin.get_app()

    database_url = os.getenv("FIREBASE_DATABASE_URL", "").strip()
    if not database_url:
        raise FirebaseConfigError("Set FIREBASE_DATABASE_URL in your .env file.")

    return firebase_admin.initialize_app(_load_credentials(), {"databaseURL": database_url})


def _as_list(value: Any, length: int) -> List[int]:
    """RTDB returns integer-keyed children as a list or a dict; normalise to a list."""
    result = [0] * length
    if isinstance(value, list):
        for i, v in enumerate(value[:length]):
            result[i] = int(v or 0)
    elif isinstance(value, dict):
        for k, v in value.items():
            idx = int(k)
            if 0 <= idx < length:
                result[idx] = int(v or 0)
    return result


class CloudPoolManager:
    """All read/write operations against the Firebase Realtime Database."""

    PEER_SAMPLE_SIZE = 20

    def __init__(self) -> None:
        get_firebase_app()
        self._root = db.reference("/")

    # ------------------------------------------------------------------ F2
    def add_comment(self, text: str, author: str = "Anonymous") -> str:
        ref = self._root.child("comments").push(
            {"text": text.strip(), "author": (author or "Anonymous").strip()[:40], "ts": time.time()}
        )
        return ref.key

    def get_comments(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        query = self._root.child("comments").order_by_key()
        if limit:
            query = query.limit_to_last(limit)
        data = query.get() or {}
        comments = [{"id": key, **value} for key, value in data.items() if isinstance(value, dict)]
        comments.sort(key=lambda c: c.get("ts", 0))
        return comments

    def clear_comments(self) -> None:
        self._root.child("comments").delete()

    # ------------------------------------------------------------------ F3
    def create_poll(self, question: str, options: List[str]) -> str:
        ref = self._root.child("polls/items").push(
            {
                "question": question.strip(),
                "options": [o.strip() for o in options],
                "counts": [0] * len(options),
                "created_at": time.time(),
                "closed": False,
            }
        )
        self._root.child("polls/active_id").set(ref.key)
        return ref.key

    def close_poll(self) -> None:
        active_id = self._root.child("polls/active_id").get()
        if active_id:
            self._root.child(f"polls/items/{active_id}/closed").set(True)
        self._root.child("polls/active_id").delete()

    def get_poll(self, poll_id: str) -> Optional[Dict[str, Any]]:
        data = self._root.child(f"polls/items/{poll_id}").get()
        if not isinstance(data, dict):
            return None
        options = list(data.get("options") or [])
        return {
            "id": poll_id,
            "question": data.get("question", ""),
            "options": options,
            "counts": _as_list(data.get("counts"), len(options)),
            "created_at": data.get("created_at", 0),
            "closed": bool(data.get("closed", False)),
        }

    def get_active_poll(self) -> Optional[Dict[str, Any]]:
        active_id = self._root.child("polls/active_id").get()
        return self.get_poll(active_id) if active_id else None

    def vote(self, poll_id: str, option_idx: int) -> None:
        """Atomically increment a vote counter (safe under concurrent votes)."""
        counter = self._root.child(f"polls/items/{poll_id}/counts/{int(option_idx)}")
        counter.transaction(lambda current: (current or 0) + 1)

    # ------------------------------------------------------------------ F5
    def push_submission(self, code: str, language: str) -> str:
        ref = self._root.child("submissions").push(
            {"code": code, "language": language, "ts": time.time()}
        )
        return ref.key

    def get_peer_submission(self, exclude_key: str, language: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return a random prior anonymous submission (preferring the same language)."""
        data = (
            self._root.child("submissions").order_by_key().limit_to_last(self.PEER_SAMPLE_SIZE + 1).get()
            or {}
        )
        peers = [
            {"id": key, **value}
            for key, value in data.items()
            if key != exclude_key and isinstance(value, dict) and value.get("code")
        ]
        if not peers:
            return None
        same_language = [p for p in peers if language and p.get("language") == language]
        return random.choice(same_language or peers)

    def count_submissions(self) -> int:
        data = self._root.child("submissions").get(shallow=True) or {}
        return len(data)


@st.cache_resource(show_spinner=False)
def get_pool_manager() -> CloudPoolManager:
    return CloudPoolManager()
