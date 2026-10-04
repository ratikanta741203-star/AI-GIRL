"""
AI-Girl / Prity AI – Main Application
OpenRouter-powered FastAPI application

Run:
    uvicorn app:app --reload --host 127.0.0.1 --port 8000

Or:
    python app.py
"""

from __future__ import annotations

import os
import json
import base64
import binascii
from io import BytesIO
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import OpenAI

from utils.document_reader import parse_attachment_file
from utils.file_generator import auto_detect_and_generate_files, GENERATED_DIR

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    print("\nWARNING: OPENROUTER_API_KEY is not set.")
    print("Create a .env file and add:")
    print("OPENROUTER_API_KEY=your_new_openrouter_key\n")


# ============================================================
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# You can change this model later.
AI_MODEL = os.getenv(
    "AI_MODEL",
    "openrouter/free"
)
AI_AUDIO_MODEL = os.getenv(
    "OPENROUTER_AUDIO_MODEL",
    "google/gemini-2.5-flash"
)


# ============================================================
# EXISTING PROJECT MODULES
# ============================================================

try:
    from config import settings
except Exception:

    class Settings:
        APP_NAME = "Prity AI"
        VERSION = "2.0.0"
        CHARACTER_NAME = "Baby"
        AI_PROVIDER = "OpenRouter"
        AI_MODEL = AI_MODEL
        WAKE_WORD = "hello baby"
        LOCAL_MODE = True
        HOST = "127.0.0.1"
        PORT = 8000
        DEBUG = True
        PROACTIVE_ENABLED = True
        DEFAULT_LANGUAGE = "en"
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    settings = Settings()


try:
    from assistant.memory import MemoryManager
except Exception:
    MemoryManager = None


try:
    from assistant.personality import PersonalityEngine
except Exception:
    PersonalityEngine = None


try:
    from assistant.planner import Planner
except Exception:
    Planner = None


try:
    from assistant.tools import ToolManager
except Exception:
    ToolManager = None


try:
    from avatar.animation import AnimationController
except Exception:
    AnimationController = None


try:
    from voice.wake_word import WakeWordDetector
except Exception:
    WakeWordDetector = None


try:
    from voice.speech_to_text import SpeechToText
except Exception:
    SpeechToText = None


try:
    from voice.text_to_speech import TextToSpeech
except Exception:
    TextToSpeech = None


# ============================================================
# GLOBAL INSTANCES
# ============================================================

memory = MemoryManager() if MemoryManager else None

personality = (
    PersonalityEngine()
    if PersonalityEngine
    else None
)

planner = (
    Planner(memory=memory)
    if Planner and memory
    else None
)

tools = ToolManager() if ToolManager else None

avatar = (
    AnimationController()
    if AnimationController
    else None
)

wake = (
    WakeWordDetector()
    if WakeWordDetector
    else None
)

stt = (
    SpeechToText()
    if SpeechToText
    else None
)

tts = (
    TextToSpeech()
    if TextToSpeech
    else None
)


# ============================================================
# AI-GIRL PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
You are Baby / Prity, an ultra-smart, friendly, and capable personal AI girl companion.

Your superpowers & capabilities:
- Multimodal Vision: Deeply analyze and explain pictures, photos, diagrams, screenshots, UI mockups, charts, and math graphs.
- Full Document Comprehension: Read, summarize, extract data, analyze, and query PDF files, Word documents (.docx), Excel spreadsheets (.xlsx, .xls, .csv), PowerPoint slide decks (.pptx), and code repositories.
- Generative Creation: You can generate PowerPoint presentations (slide by slide with titles and bullet points), create Excel data tables, draft Word documents, and write professional scripts.
- World-class Programming & Code Output:
  * When writing code, ALWAYS enclose it in clean Markdown code blocks specifying the exact language (e.g. ```python, ```javascript, ```html, ```css, ```json, ```cpp, ```sql, ```bash, etc.).
  * Write clean, production-grade, bug-free code with clear explanations.
  * Provide complete solutions without unnecessary placeholders.

Your personality:
- Friendly, warm, caring, intelligent, articulate, and conversational.
- Keep answers insightful, clear, and structured with clean markdown headers and bullet points.
- Never claim to be a physical human; you are a cutting-edge personal AI companion running locally for the user.
"""


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n========================================")
    print("        PRITY AI / AI-GIRL")
    print("========================================")
    print(f"Character : {getattr(settings, 'CHARACTER_NAME', 'Baby')}")
    print("Provider  : OpenRouter")
    print(f"Model     : {AI_MODEL}")
    print(
        f"Wake word : "
        f"{getattr(settings, 'WAKE_WORD', 'hello baby')}"
    )
    print(
        f"Dashboard : "
        f"http://{getattr(settings, 'HOST', '127.0.0.1')}:"
        f"{getattr(settings, 'PORT', 8000)}"
    )
    print("========================================\n")

    if OPENROUTER_API_KEY:
        print("OpenRouter API key: LOADED")
    else:
        print("OpenRouter API key: NOT LOADED")

    yield

    print("\nBaby AI shutting down...\n")


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title=getattr(settings, "APP_NAME", "Prity AI"),
    version=getattr(settings, "VERSION", "2.0.0"),
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# FRONTEND
# ============================================================

try:
    frontend_dir = settings.BASE_DIR / "frontend"
except Exception:
    frontend_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "frontend"
    )

if hasattr(frontend_dir, "exists"):

    if frontend_dir.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(frontend_dir)),
            name="static"
        )

else:

    if os.path.exists(frontend_dir):
        app.mount(
            "/static",
            StaticFiles(directory=str(frontend_dir)),
            name="static"
        )


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class ChatAttachment(BaseModel):

    name: str = Field(..., min_length=1, max_length=255)

    media_type: str = Field(default="application/octet-stream", max_length=100)

    data: str = Field(..., min_length=1)


class ChatRequest(BaseModel):

    message: str = Field(default="", max_length=4000)

    stream: bool = False

    attachments: List[ChatAttachment] = Field(
        default_factory=list,
        max_length=4
    )


class ChatResponse(BaseModel):

    reply: str

    expression: str = "neutral"

    character: str = "Baby"


class MemorySetRequest(BaseModel):

    category: str

    key: str

    value: str


class TaskCreateRequest(BaseModel):

    title: str

    description: str = ""

    priority: int = 0


class PlanDayRequest(BaseModel):

    wake_time: str = "08:00"

    sleep_time: str = "23:00"


class SettingsUpdate(BaseModel):

    personality_style: Optional[str] = None

    proactive_enabled: Optional[bool] = None

    local_mode: Optional[bool] = None


# ============================================================
# MEMORY → OPENROUTER MESSAGE HISTORY
# ============================================================

def get_conversation_messages():

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    if not memory:
        return messages

    try:

        history = memory.get_recent_messages(
            limit=20
        )

        if not history:
            return messages

        for item in history:

            if not isinstance(item, dict):
                continue

            role = item.get("role")

            content = (
                item.get("content")
                or item.get("message")
                or item.get("text")
            )

            if role not in ["user", "assistant"]:
                continue

            if not content:
                continue

            messages.append(
                {
                    "role": role,
                    "content": str(content)
                }
            )

    except Exception as error:

        print(
            f"Memory history warning: {error}"
        )

    return messages


# ============================================================
# SAVE MESSAGE TO MEMORY
# ============================================================

def save_message(
    role: str,
    content: str
):

    if not memory:
        return

    try:

        # Try common memory APIs.

        if hasattr(memory, "add_message"):

            memory.add_message(
                role=role,
                content=content
            )

        elif hasattr(memory, "save_message"):

            memory.save_message(
                role=role,
                content=content
            )

    except Exception as error:

        print(
            f"Memory save warning: {error}"
        )


# ============================================================
# OPENROUTER CHAT
# ============================================================

MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_ATTACHMENT_BYTES = 12 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS = 150_000


def build_attachment_content(
    message: str,
    attachments: List[ChatAttachment]
) -> tuple[List[dict], bool, bool]:

    content = []
    audio_attached = False
    vision_attached = False
    total_bytes = 0
    text_parts = []

    if message:
        text_parts.append(message)
    else:
        text_parts.append(
            "Please review the attached file(s) and provide a comprehensive, intelligent answer."
        )

    for attachment in attachments:
        encoded = attachment.data
        max_encoded_length = ((MAX_ATTACHMENT_BYTES + 2) // 3) * 4

        if len(encoded) > max_encoded_length:
            raise HTTPException(
                status_code=413,
                detail=f"{attachment.name} is larger than the 8 MB limit."
            )

        try:
            file_bytes = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise HTTPException(
                status_code=400,
                detail=f"{attachment.name} is not valid base64 file data."
            ) from error

        if len(file_bytes) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{attachment.name} is larger than the 8 MB limit."
            )

        total_bytes += len(file_bytes)
        if total_bytes > MAX_TOTAL_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Attachments exceed the 12 MB total limit."
            )

        # Use unified document and image reader
        try:
            multimodal_payload, extracted_text = parse_attachment_file(
                attachment.name,
                file_bytes,
                attachment.media_type
            )
            if multimodal_payload:
                if multimodal_payload.get("type") == "image_url":
                    vision_attached = True
                    content.append(multimodal_payload)
                elif multimodal_payload.get("type") == "input_audio":
                    audio_attached = True
                    content.append(multimodal_payload)
            if extracted_text:
                text_parts.append(extracted_text)
        except Exception as err:
            text_parts.append(f"[Error reading {attachment.name}: {err}]")

    combined_text = "\n\n".join(text_parts)
    if len(combined_text) > MAX_EXTRACTED_TEXT_CHARS:
        combined_text = combined_text[:MAX_EXTRACTED_TEXT_CHARS] + "\n\n[...Extracted content truncated at 150k characters...]"

    content.insert(0, {
        "type": "text",
        "text": combined_text
    })
    return content, vision_attached, audio_attached


def ask_openrouter(
    user_message: str,
    attachments: Optional[List[ChatAttachment]] = None
) -> str:

    if not OPENROUTER_API_KEY:

        return (
            "OpenRouter API key is not configured. "
            "Please add OPENROUTER_API_KEY to your .env file."
        )

    messages = get_conversation_messages()

    request_content = user_message
    model = AI_MODEL

    if attachments:
        request_content, vision_attached, audio_attached = build_attachment_content(
            user_message,
            attachments
        )
        if vision_attached:
            # Route to high-accuracy Vision model
            model = os.getenv("OPENROUTER_VISION_MODEL", "google/gemini-2.5-flash")
        elif audio_attached:
            model = AI_AUDIO_MODEL

    messages.append({
        "role": "user",
        "content": request_content
    })

    try:

        response = client.chat.completions.create(

            model=model,

            messages=messages,

            temperature=0.7,

            max_tokens=2048,
        )

        if not response.choices:

            return (
                "I didn't receive a response from "
                "the AI model."
            )

        reply = response.choices[0].message.content

        if not reply:

            return (
                "I received an empty response "
                "from the AI model."
            )

        reply = str(reply).strip()

        save_message(
            "user",
            user_message
        )

        save_message(
            "assistant",
            reply
        )

        return reply

    except Exception as error:

        print(
            f"OpenRouter error: {error}"
        )

        return (
            "Sorry, I couldn't connect to "
            "OpenRouter right now.\n\n"
            f"Error: {error}"
        )


# ============================================================
# ASYNC OPENROUTER CHAT
# ============================================================

async def ask_openrouter_async(
    user_message: str,
    attachments: Optional[List[ChatAttachment]] = None
) -> str:

    # Run the synchronous OpenRouter client
    # without blocking the FastAPI event loop.

    import asyncio

    return await asyncio.to_thread(
        ask_openrouter,
        user_message,
        attachments
    )


# ============================================================
# EXPRESSION
# ============================================================

def get_expression(
    reply: str
) -> str:

    if avatar:

        try:

            return (
                avatar.expressions
                .infer_from_text(
                    reply,
                    role="assistant"
                )
            )

        except Exception:
            pass

    text = reply.lower()

    if any(
        word in text
        for word in [
            "haha",
            "funny",
            "lol"
        ]
    ):
        return "happy"

    if any(
        word in text
        for word in [
            "sorry",
            "sad"
        ]
    ):
        return "sad"

    if any(
        word in text
        for word in [
            "wow",
            "amazing"
        ]
    ):
        return "surprised"

    if "?" in reply:
        return "thinking"

    return "neutral"


# ============================================================
# HOME
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def root():

    try:

        index = frontend_dir / "index.html"

    except Exception:

        index = os.path.join(
            frontend_dir,
            "index.html"
        )

    if hasattr(index, "exists"):

        if index.exists():
            return FileResponse(index)

    else:

        if os.path.exists(index):
            return FileResponse(index)

    return HTMLResponse(
        """
        <html>
        <body>
            <h1>Prity AI is running ❤️</h1>
            <p>Frontend not found.</p>
            <p>Place index.html inside /frontend</p>
        </body>
        </html>
        """
    )


@app.get("/api/download/apk")
async def download_apk():
    try:
        apk_path = frontend_dir / "Prity_AI.apk"
    except Exception:
        apk_path = os.path.join(frontend_dir, "Prity_AI.apk")
    
    # Do not serve a placeholder archive: Android rejects it as invalid.
    if not os.path.exists(apk_path) or os.path.getsize(apk_path) < 1024 * 1024:
        raise HTTPException(
            status_code=404,
            detail="An Android APK has not been published. Install Prity AI from your browser instead."
        )

    return FileResponse(
        apk_path,
        filename="Prity_AI_v2.0.apk",
        media_type="application/vnd.android.package-archive"
    )



# ============================================================
# STATUS
# ============================================================

@app.get("/api/status")
async def status():

    return {
        "app": getattr(
            settings,
            "APP_NAME",
            "Prity AI"
        ),

        "version": getattr(
            settings,
            "VERSION",
            "2.0.0"
        ),

        "character": getattr(
            settings,
            "CHARACTER_NAME",
            "Baby"
        ),

        "provider": "OpenRouter",

        "model": AI_MODEL,

        "openrouter": bool(
            OPENROUTER_API_KEY
        ),

        "local_mode": getattr(
            settings,
            "LOCAL_MODE",
            True
        ),

        "wake_word": (
            wake.status()
            if wake and hasattr(wake, "status")
            else "unavailable"
        ),

        "stt": (
            stt.status()
            if stt and hasattr(stt, "status")
            else "unavailable"
        ),

        "tts": (
            tts.status()
            if tts and hasattr(tts, "status")
            else "unavailable"
        ),

        "avatar": (
            avatar.update()
            if avatar and hasattr(avatar, "update")
            else {}
        ),

        "proactive": getattr(
            settings,
            "PROACTIVE_ENABLED",
            True
        ),
    }


@app.get("/api/download/file/{filename}")
async def download_generated_file(filename: str):
    safe_name = os.path.basename(filename)
    file_path = GENERATED_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested file not found.")
    
    media_types = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
    }
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(file_path, filename=safe_name, media_type=media_type)


# ============================================================
# NORMAL CHAT
# ============================================================

@app.post(
    "/api/chat",
    response_model=ChatResponse
)
async def chat(
    req: ChatRequest
):

    message = req.message.strip()

    if not message and not req.attachments:

        raise HTTPException(
            status_code=400,
            detail="Type a message or attach a file."
        )

    if len(req.attachments) > 4:
        raise HTTPException(
            status_code=400,
            detail="You can attach up to 4 files per message."
        )

    if avatar:

        try:
            avatar.expressions.set_state(
                "thinking"
            )
        except Exception:
            pass

    reply = await ask_openrouter_async(
        message,
        req.attachments
    )

    # Process & auto-generate PPTX / Excel / Word if requested
    try:
        reply = auto_detect_and_generate_files(message, reply)
    except Exception as err:
        print(f"File generation hook warning: {err}")

    expression = get_expression(
        reply
    )

    if avatar:

        try:
            avatar.expressions.set_state(
                "idle"
            )
        except Exception:
            pass

    return ChatResponse(
        reply=reply,
        expression=expression,
        character=getattr(
            settings,
            "CHARACTER_NAME",
            "Baby"
        )
    )


# ============================================================
# WEBSOCKET CHAT
# ============================================================

@app.websocket("/ws/chat")
async def ws_chat(
    websocket: WebSocket
):

    await websocket.accept()

    try:

        while True:

            data = await websocket.receive_text()

            try:

                payload = json.loads(data)

            except json.JSONDecodeError:

                payload = {
                    "message": data
                }

            message = str(
                payload.get(
                    "message",
                    ""
                )
            ).strip()

            if not message:
                continue

            await websocket.send_json(
                {
                    "type": "status",
                    "state": "thinking"
                }
            )

            if avatar:

                try:

                    avatar.expressions.set_state(
                        "thinking"
                    )

                except Exception:
                    pass

            reply = await ask_openrouter_async(
                message
            )

            # Simple streaming simulation.
            # This keeps your existing WebSocket
            # frontend compatible.

            words = reply.split(" ")

            for index, word in enumerate(words):

                token = word

                if index < len(words) - 1:
                    token += " "

                await websocket.send_json(
                    {
                        "type": "token",
                        "content": token
                    }
                )

            expression = get_expression(
                reply
            )

            await websocket.send_json(
                {
                    "type": "done",
                    "reply": reply,
                    "expression": expression
                }
            )

            if avatar:

                try:

                    avatar.expressions.set_state(
                        "idle"
                    )

                except Exception:
                    pass

    except WebSocketDisconnect:

        pass

    except Exception as error:

        print(
            f"WebSocket error: {error}"
        )

        try:

            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(error)
                }
            )

        except Exception:
            pass


# ============================================================
# MEMORY
# ============================================================

@app.get(
    "/api/memory/{category}"
)
async def list_memory(
    category: str
):

    if not memory:

        return []

    try:

        return memory.list_by_category(
            category
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.post("/api/memory")
async def set_memory(
    req: MemorySetRequest
):

    if not memory:

        raise HTTPException(
            status_code=503,
            detail="Memory system unavailable."
        )

    try:

        mid = memory.set(
            req.category,
            req.key,
            req.value
        )

        return {
            "id": mid,
            "ok": True
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.delete(
    "/api/memory/{entry_id}"
)
async def delete_memory(
    entry_id: int
):

    if not memory:

        raise HTTPException(
            status_code=503,
            detail="Memory system unavailable."
        )

    ok = memory.delete(
        entry_id
    )

    if not ok:

        raise HTTPException(
            status_code=404,
            detail="Memory entry not found"
        )

    return {
        "ok": True
    }


@app.post("/api/memory/clear")
async def clear_all_memory():

    if memory:

        memory.clear_all()

    return {
        "ok": True,
        "message": "All memory cleared"
    }


# ============================================================
# CONVERSATION
# ============================================================

@app.get("/api/conversation")
async def get_conversation(
    limit: int = 50
):

    if not memory:

        return []

    try:

        return memory.get_recent_messages(
            limit=limit
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.delete("/api/conversation")
async def clear_conversation():

    if memory:

        memory.clear_conversation()

    return {
        "ok": True
    }


# ============================================================
# TASKS
# ============================================================

@app.get("/api/tasks")
async def list_tasks(
    status: Optional[str] = None
):

    if not memory:

        return []

    try:

        return memory.list_tasks(
            status=status
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.post("/api/tasks")
async def create_task(
    req: TaskCreateRequest
):

    if not memory:

        raise HTTPException(
            status_code=503,
            detail="Memory system unavailable."
        )

    try:

        tid = memory.create_task(
            req.title,
            req.description,
            req.priority
        )

        return {
            "id": tid,
            "ok": True
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.post(
    "/api/tasks/{task_id}/complete"
)
async def complete_task(
    task_id: int
):

    if not memory:

        raise HTTPException(
            status_code=503,
            detail="Memory system unavailable."
        )

    ok = memory.complete_task(
        task_id
    )

    if not ok:

        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "ok": True
    }


@app.post("/api/tasks/{task_id}/reopen")
async def reopen_task(task_id: int):
    """Return a completed task to the pending list."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory system unavailable.")

    if not memory.uncomplete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    return {"ok": True}


@app.delete(
    "/api/tasks/{task_id}"
)
async def delete_task(
    task_id: int
):

    if not memory:

        raise HTTPException(
            status_code=503,
            detail="Memory system unavailable."
        )

    ok = memory.delete_task(
        task_id
    )

    if not ok:

        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "ok": True
    }


# ============================================================
# PLANNER
# ============================================================

@app.post("/api/plan")
async def plan_day(
    req: PlanDayRequest
):

    if not planner:

        raise HTTPException(
            status_code=503,
            detail="Planner unavailable."
        )

    schedule = planner.plan_day(
        wake_time=req.wake_time,
        sleep_time=req.sleep_time
    )

    return {
        "schedule": schedule,
        "text": planner.format_schedule(
            schedule
        )
    }


# ============================================================
# AVATAR
# ============================================================

@app.get("/api/avatar/state")
async def avatar_state():

    if not avatar:

        return {
            "state": "idle"
        }

    try:

        return avatar.update()

    except Exception as error:

        return {
            "state": "idle",
            "error": str(error)
        }


@app.post(
    "/api/avatar/state/{state}"
)
async def set_avatar_state(
    state: str
):

    if not avatar:

        return {
            "state": state
        }

    try:

        avatar.expressions.set_state(
            state
        )

        return avatar.update()

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# TOOLS
# ============================================================

@app.post("/api/tools/open")
async def open_app(
    name: str
):

    if not tools:

        raise HTTPException(
            status_code=503,
            detail="Tool manager unavailable."
        )

    try:

        return {
            "result":
                tools.open_application(name)
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# SETTINGS
# ============================================================

@app.get("/api/settings")
async def get_settings():

    personality_style = "default"

    if personality:

        try:

            personality_style = (
                personality.style
            )

        except Exception:
            pass

    return {

        "character_name":
            getattr(
                settings,
                "CHARACTER_NAME",
                "Baby"
            ),

        "personality_style":
            personality_style,

        "wake_word":
            getattr(
                settings,
                "WAKE_WORD",
                "hello baby"
            ),

        "local_mode":
            getattr(
                settings,
                "LOCAL_MODE",
                True
            ),

        "proactive_enabled":
            getattr(
                settings,
                "PROACTIVE_ENABLED",
                True
            ),

        "ai_provider":
            "OpenRouter",

        "ai_model":
            AI_MODEL,

        "default_language":
            getattr(
                settings,
                "DEFAULT_LANGUAGE",
                "en"
            ),

        "api_key_loaded":
            bool(
                OPENROUTER_API_KEY
            )
    }


@app.post("/api/settings")
async def update_settings(
    req: SettingsUpdate
):

    if (
        req.personality_style
        and personality
    ):

        try:

            personality.set_style(
                req.personality_style
            )

        except Exception:
            pass

    return {
        "ok": True,
        "settings":
            await get_settings()
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "service": "Baby AI",
        "provider": "OpenRouter",
        "model": AI_MODEL,
        "api_key_configured":
            bool(OPENROUTER_API_KEY)
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "app:app",

        host=getattr(
            settings,
            "HOST",
            "127.0.0.1"
        ),

        port=getattr(
            settings,
            "PORT",
            8000
        ),

        reload=getattr(
            settings,
            "DEBUG",
            True
        )
    )
