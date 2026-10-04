"""
AI Brain - model-agnostic reasoning layer.
Supports Prity (local), Gemini, and OpenAI-compatible endpoints.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator, Dict, List, Optional

import httpx

from config import settings
from assistant.personality import PersonalityEngine
from assistant.memory import MemoryManager


class Brain:
    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
        personality: Optional[PersonalityEngine] = None,
    ):
        self.memory = memory or MemoryManager()
        self.personality = personality or PersonalityEngine()
        self.provider = settings.AI_PROVIDER

    async def chat(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Main entry point. Returns full reply or streams tokens."""
        if history is None:
            history = self.memory.get_recent_messages(limit=settings.MAX_CONVERSATION_HISTORY)

        # Persist user message
        self.memory.add_message("user", user_message)

        system_prompt = self.personality.build_system_prompt(
            user_context=self.memory.get_user_context_summary()
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        if stream:
            return self._stream_reply(messages)
        else:
            reply = await self._full_reply(messages)
            self.memory.add_message("assistant", reply)
            return reply

    async def _full_reply(self, messages: List[Dict[str, str]]) -> str:
        # "prity" and "local" use the local OpenAI-compatible server
        if self.provider in ("prity", "ollama", "openai", "local"):
            return await self._openai_compatible(messages, stream=False)
        elif self.provider == "gemini":
            return await self._gemini(messages)
        else:
            return await self._openai_compatible(messages, stream=False)

    async def _stream_reply(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        full = []
        async for token in self._openai_compatible_stream(messages):
            full.append(token)
            yield token
        self.memory.add_message("assistant", "".join(full))

    # ── OpenAI-compatible (Ollama, LM Studio, etc.) ──────
    async def _openai_compatible(self, messages: List[Dict], stream: bool = False) -> str:
        base = settings.OPENAI_BASE_URL.rstrip("/")
        # Always use the real local model name for the server request
        model = settings.OPENAI_MODEL
        headers = {"Content-Type": "application/json"}
        if settings.OPENAI_API_KEY:
            headers["Authorization"] = f"Bearer {settings.OPENAI_API_KEY}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_TOKENS,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                r = await client.post(f"{base}/chat/completions", json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                return (
                    f"I'm having trouble connecting to my AI model ({self.provider}). "
                    f"Please check that the model server is running. Details: {e}"
                )

    async def _openai_compatible_stream(
        self, messages: List[Dict]
    ) -> AsyncGenerator[str, None]:
        base = settings.OPENAI_BASE_URL.rstrip("/")
        model = settings.OPENAI_MODEL
        headers = {"Content-Type": "application/json"}
        if settings.OPENAI_API_KEY:
            headers["Authorization"] = f"Bearer {settings.OPENAI_API_KEY}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_TOKENS,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST", f"{base}/chat/completions", json=payload, headers=headers
                ) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except Exception:
                            continue
            except Exception as e:
                yield (
                    f"I'm having trouble connecting to my AI model. "
                    f"Please check that the Prity model server is running. ({e})"
                )

    # ── Gemini ───────────────────────────────────────────
    async def _gemini(self, messages: List[Dict]) -> str:
        if not settings.GEMINI_API_KEY:
            return "Gemini API key is not configured. Set GEMINI_API_KEY in .env"

        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)

            # Convert messages to Gemini format
            system = ""
            contents = []
            for m in messages:
                if m["role"] == "system":
                    system = m["content"]
                elif m["role"] == "user":
                    contents.append({"role": "user", "parts": [m["content"]]})
                elif m["role"] == "assistant":
                    contents.append({"role": "model", "parts": [m["content"]]})

            if system:
                model = genai.GenerativeModel(
                    settings.GEMINI_MODEL,
                    system_instruction=system,
                )

            response = model.generate_content(
                contents,
                generation_config={
                    "temperature": settings.AI_TEMPERATURE,
                    "max_output_tokens": settings.AI_MAX_TOKENS,
                },
            )
            return response.text.strip()
        except Exception as e:
            return f"Gemini error: {e}"
