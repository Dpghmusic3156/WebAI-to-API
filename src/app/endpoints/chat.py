# src/app/endpoints/chat.py
import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.logger import logger
from app.config import CONFIG
from schemas.request import GeminiModels, GeminiRequest, OpenAIChatRequest
from app.services.gemini_client import get_gemini_client, GeminiClientNotInitializedError
from app.services.session_manager import get_translate_session_manager

router = APIRouter()


@router.get("/v1/models")
async def list_models():
    """List available models in OpenAI-compatible format."""
    now = int(time.time())
    models = [
        {
            "id": m.value,
            "object": "model",
            "created": now,
            "owned_by": "google",
        }
        for m in GeminiModels
    ]
    return {"object": "list", "data": models}

@router.post("/translate")
async def translate_chat(request: GeminiRequest):
    try:
        gemini_client = get_gemini_client()
    except GeminiClientNotInitializedError as e:
        raise HTTPException(status_code=503, detail=str(e))

    session_manager = get_translate_session_manager()
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager is not initialized.")
    try:
        # This call now correctly uses the fixed session manager
        response = await session_manager.get_response(request.model, request.message, request.files)
        return {"response": response.text}
    except Exception as e:
        logger.error(f"Error in /translate endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error during translation: {str(e)}")

def convert_to_openai_format(response_text: str, model: str, stream: bool = False):
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion.chunk" if stream else "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }

def _extract_content(content) -> str:
    """Extract text from content that may be a string or a list of content parts (OpenAI multimodal format)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return str(content) if content else ""


async def _stream_response(response_text: str, model: str):
    """Yield SSE chunks in OpenAI streaming format."""
    completion_id = f"chatcmpl-{int(time.time())}"
    created = int(time.time())

    # First chunk: role
    first_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(first_chunk)}\n\n"

    # Content chunk
    content_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {"content": response_text}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(content_chunk)}\n\n"

    # Final chunk
    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/v1/chat/completions")
async def chat_completions(request: OpenAIChatRequest):
    try:
        gemini_client = get_gemini_client()
    except GeminiClientNotInitializedError as e:
        raise HTTPException(status_code=503, detail=str(e))

    is_stream = request.stream if request.stream is not None else False

    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    # Build conversation prompt with system prompt and full history
    conversation_parts = []

    for msg in request.messages:
        role = msg.get("role", "user")
        content = _extract_content(msg.get("content", ""))
        if not content:
            continue

        if role == "system":
            conversation_parts.append(f"System: {content}")
        elif role == "user":
            conversation_parts.append(f"User: {content}")
        elif role == "assistant":
            conversation_parts.append(f"Assistant: {content}")

    if not conversation_parts:
        raise HTTPException(status_code=400, detail="No valid messages found.")

    final_prompt = "\n\n".join(conversation_parts)

    if not request.model:
        raise HTTPException(status_code=400, detail="Model not specified in the request.")

    try:
        response = await gemini_client.generate_content(message=final_prompt, model=request.model.value, files=None)
        if is_stream:
            return StreamingResponse(
                _stream_response(response.text, request.model.value),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return convert_to_openai_format(response.text, request.model.value, is_stream)
    except Exception as e:
        logger.error(f"Error in /v1/chat/completions endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat completion: {str(e)}")
