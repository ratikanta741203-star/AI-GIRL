"""
Wake Word Detection

Primary strategy for this foundation:
- Browser-side continuous listening with Web Speech API (simple & zero install)
- Optional local engines (Porcupine / openWakeWord) can be plugged in later.

The backend simply exposes the configured wake phrase.
"""

from config import settings


class WakeWordDetector:
    def __init__(self, phrase: str | None = None):
        self.phrase = (phrase or settings.WAKE_WORD).lower().strip()
        self.enabled = settings.WAKE_WORD_ENABLED

    def get_phrase(self) -> str:
        return self.phrase

    def is_wake(self, transcript: str) -> bool:
        """Simple contains-check. Real engines do this on audio stream."""
        if not self.enabled:
            return True  # always "awake" when disabled
        text = transcript.lower().strip()
        return self.phrase in text or text.startswith(self.phrase.split()[0])

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "phrase": self.phrase,
            "engine": "browser_or_simple",
        }
