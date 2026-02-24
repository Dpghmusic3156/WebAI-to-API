# src/app/services/session_manager.py
import asyncio
from app.logger import logger
from app.services.gemini_client import get_gemini_client, GeminiClientNotInitializedError


class SessionManager:
    def __init__(self, client):
        self.client = client
        self.session = None
        self.model = None
        self.lock = asyncio.Lock()

    async def get_response(self, model, message, images):
        async with self.lock:
            # Start a new session if none exists or the model has changed
            if self.session is None or self.model != model:
                model_value = model.value if hasattr(model, "value") else model
                self.session = self.client.start_chat(model=model_value)
                self.model = model

            try:
                return await self.session.send_message(prompt=message, files=images)
            except Exception as e:
                logger.error(f"Error in session get_response: {e}", exc_info=True)
                raise


# Dict lưu session theo session_id (dùng cho /gemini-chat)
_chat_sessions: dict[str, SessionManager] = {}

# Singleton session cho /translate
_translate_session_manager: SessionManager | None = None


def get_or_create_chat_session(session_id: str) -> SessionManager:
    """Lấy session theo ID, tạo mới nếu chưa có."""
    if session_id not in _chat_sessions:
        client = get_gemini_client()
        _chat_sessions[session_id] = SessionManager(client)
        logger.info(f"Created new chat session: {session_id}")
    return _chat_sessions[session_id]


def delete_chat_session(session_id: str) -> bool:
    """Xoá session theo ID. Trả về True nếu tồn tại và đã xoá."""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
        logger.info(f"Deleted chat session: {session_id}")
        return True
    return False


def get_translate_session_manager() -> SessionManager | None:
    return _translate_session_manager


def init_session_managers():
    """Khởi tạo session manager cho /translate."""
    global _translate_session_manager
    try:
        client = get_gemini_client()
        _translate_session_manager = SessionManager(client)
        logger.info("Translate session manager initialized.")
    except GeminiClientNotInitializedError as e:
        logger.warning(f"Session managers not initialized: Gemini client not available. Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error initializing session managers: {e}", exc_info=True)


# --- Giữ backward compat cho code cũ nếu có ---
def get_gemini_chat_manager() -> SessionManager | None:
    """Deprecated: dùng get_or_create_chat_session() thay thế."""
    return None
