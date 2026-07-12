"""
memory.py — session memory + long-term fact store for the Live AI Assistant.

Two layers:
  SessionMemory   — the full message history for one chat session, persisted
                     to memory_store/session_<id>.json so context survives a restart.
  LongTermMemory   — a small JSON fact store built with /remember, injected
                     into the system prompt on every turn via as_prompt_block().
"""

import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

MEMORY_DIR = Path("memory_store")
MEMORY_DIR.mkdir(exist_ok=True)

LONG_TERM_FILE = MEMORY_DIR / "long_term.json"


class SessionMemory:
    """Holds the full message history for one chat session and persists it to disk."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or time.strftime("%Y%m%d_%H%M%S")
        self.path = MEMORY_DIR / f"session_{self.session_id}.json"
        self.messages: List[Dict] = []
        if self.path.exists():
            self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.messages = []

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)

    def add(self, role: str, content):
        """content is either a plain string or a list of Anthropic content blocks (dicts)."""
        self.messages.append({"role": role, "content": content})
        self.save()

    def as_api_messages(self) -> List[Dict]:
        """Return messages exactly as the Anthropic Messages API expects them."""
        return self.messages

    @staticmethod
    def list_sessions() -> List[str]:
        return sorted(p.stem.replace("session_", "") for p in MEMORY_DIR.glob("session_*.json"))


class LongTermMemory:
    """Small JSON fact store the user builds up with /remember, injected into every system prompt."""

    def __init__(self):
        self.facts: List[Dict] = []
        self._load()

    def _load(self):
        if LONG_TERM_FILE.exists():
            try:
                with open(LONG_TERM_FILE, "r", encoding="utf-8") as f:
                    self.facts = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.facts = []

    def _save(self):
        with open(LONG_TERM_FILE, "w", encoding="utf-8") as f:
            json.dump(self.facts, f, indent=2, ensure_ascii=False)

    def remember(self, fact: str) -> Dict:
        entry = {
            "id": str(uuid.uuid4())[:8],
            "fact": fact.strip(),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.facts.append(entry)
        self._save()
        return entry

    def forget(self, fact_id: str) -> bool:
        before = len(self.facts)
        self.facts = [f for f in self.facts if f["id"] != fact_id]
        if len(self.facts) != before:
            self._save()
            return True
        return False

    def all(self) -> List[Dict]:
        return self.facts

    def as_prompt_block(self, limit: int = 30) -> str:
        """Render remembered facts as a block to splice into the system prompt."""
        if not self.facts:
            return ""
        recent = self.facts[-limit:]
        lines = "\n".join(f"- {f['fact']} (saved {f['created_at']})" for f in recent)
        return (
            "The user has asked you to remember the following facts about them "
            "across sessions. Use them naturally when relevant — don't recite "
            "the list unprompted:\n" + lines
        )