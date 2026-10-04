"""
Speech-to-Text abstraction.

Default: browser Web Speech API (handled in frontend).
Optional: faster-whisper / openai-whisper on the backend.
"""

from config import settings


class SpeechToText:
    def __init__(self):
        self.engine = settings.STT_ENGINE

    def status(self) -> dict:
        return {
            "engine": self.engine,
            "note": (
                "Primary STT is done in the browser via Web Speech API. "
                "Local Whisper can be enabled later by setting STT_ENGINE=whisper "
                "and installing faster-whisper."
            ),
        }

    async def transcribe_file(self, audio_path: str, language: str = "en") -> str:
        """Placeholder for local Whisper transcription."""
        if self.engine != "whisper":
            return (
                "Backend STT is set to browser mode. "
                "Switch STT_ENGINE to 'whisper' and install faster-whisper to use this."
            )
        try:
            # Example integration point (commented – install faster-whisper first)
            # from faster_whisper import WhisperModel
            # model = WhisperModel("base", device="cpu", compute_type="int8")
            # segments, _ = model.transcribe(audio_path, language=language)
            # return " ".join(s.text for s in segments).strip()
            return "[Whisper transcription would appear here]"
        except Exception as e:
            return f"STT error: {e}"
