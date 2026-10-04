"""
Text-to-Speech abstraction.

Default: browser speechSynthesis (frontend).
Optional: edge-tts, Piper, etc.
"""

from config import settings


class TextToSpeech:
    def __init__(self):
        self.engine = settings.TTS_ENGINE
        self.voice = settings.TTS_VOICE
        self.rate = settings.TTS_RATE
        self.pitch = settings.TTS_PITCH

    def status(self) -> dict:
        return {
            "engine": self.engine,
            "voice": self.voice,
            "rate": self.rate,
            "pitch": self.pitch,
            "note": (
                "Primary TTS runs in the browser. "
                "For local high-quality TTS install edge-tts or Piper and set TTS_ENGINE."
            ),
        }

    async def synthesize(self, text: str, output_path: str | None = None) -> str:
        """Placeholder for server-side TTS."""
        if self.engine == "browser" or self.engine == "none":
            return "TTS is handled by the browser speechSynthesis API."
        if self.engine == "edge":
            try:
                # import edge_tts
                # communicate = edge_tts.Communicate(text, self.voice)
                # await communicate.save(output_path or "output.mp3")
                return f"[edge-tts would save audio for: {text[:40]}...]"
            except Exception as e:
                return f"edge-tts error: {e}"
        return f"TTS engine '{self.engine}' not fully configured yet."
