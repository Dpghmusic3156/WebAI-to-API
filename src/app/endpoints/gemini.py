# src/app/endpoints/gemini.py
from pathlib import Path
from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException

from app.logger import logger
from app.services.gemini_client import GeminiClientNotInitializedError, get_gemini_client
from app.services.telegram_notifier import TelegramNotifier
from app.services.session_manager import get_or_create_chat_session
from app.utils.image_utils import cleanup_temp_files, serialize_response_images
from schemas.request import GeminiRequest

router = APIRouter()


def _get_cookies(gemini_client) -> dict:
    """Extract session cookies from the underlying Gemini web client."""
    try:
        return dict(gemini_client.client.cookies)
    except Exception:
        return {}


@router.post("/gemini")
async def gemini_generate(request: GeminiRequest):
    """
    Stateless content generation.

    Response includes:
    - ``response``: generated text
    - ``images``: list of web/generated images (URL + base64), if any
    - ``thoughts``: chain-of-thought text (thinking models only), if any
    """
    try:
        gemini_client = get_gemini_client()
    except GeminiClientNotInitializedError as e:
        raise HTTPException(status_code=503, detail=str(e))

    file_paths: List[Path] = [Path(f) for f in request.files] if request.files else []

    try:
        response = await gemini_client.generate_content(
            request.message, request.model.value, files=file_paths or None
        )

        images = await serialize_response_images(response, gemini_cookies=_get_cookies(gemini_client))

        result: dict = {"response": response.text}
        if images:
            result["images"] = images
        if response.thoughts:
            result["thoughts"] = response.thoughts
        return result

    except Exception as e:
        logger.error(f"Error in /gemini endpoint: {e}", exc_info=True)
        err_str = str(e)
        err_lower = err_str.lower()
        notifier = TelegramNotifier.get_instance()
        if "auth" in err_lower or "cookie" in err_lower:
            await notifier.notify_error("auth", "Authentication failed", "/gemini", err_str)
        else:
            await notifier.notify_error("500", "Unexpected error", "/gemini", err_str)
        raise HTTPException(status_code=500, detail=f"Error generating content: {err_str}")


@router.post("/gemini-chat")
async def gemini_chat(request: GeminiRequest):
    """
    Stateful chat with persistent session context.

    Pass ``session_id`` từ response trước để tiếp tục cuộc trò chuyện.
    Nếu không có ``session_id``, một session mới sẽ được tạo và ID trả về trong response.

    Response includes:
    - ``response``: generated text
    - ``session_id``: ID để tiếp tục cuộc trò chuyện ở request tiếp theo
    - ``images``: list of web/generated images (URL + base64), if any
    - ``thoughts``: chain-of-thought text (thinking models only), if any
    """
    import uuid
    try:
        gemini_client = get_gemini_client()
    except GeminiClientNotInitializedError as e:
        raise HTTPException(status_code=503, detail=str(e))

    sid = request.session_id or str(uuid.uuid4())

    try:
        session_manager = get_or_create_chat_session(sid)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not create session: {e}")

    try:
        response = await session_manager.get_response(request.model, request.message, request.files)

        images = await serialize_response_images(response, gemini_cookies=_get_cookies(gemini_client))

        result: dict = {"response": response.text, "session_id": sid}
        if images:
            result["images"] = images
        if response.thoughts:
            result["thoughts"] = response.thoughts
        return result

    except Exception as e:
        logger.error(f"Error in /gemini-chat endpoint: {e}", exc_info=True)
        err_str = str(e)
        err_lower = err_str.lower()
        notifier = TelegramNotifier.get_instance()
        if "auth" in err_lower or "cookie" in err_lower:
            await notifier.notify_error("auth", "Authentication failed", "/gemini-chat", err_str)
        else:
            await notifier.notify_error("500", "Unexpected error", "/gemini-chat", err_str)
        raise HTTPException(status_code=500, detail=f"Error in chat: {err_str}")
