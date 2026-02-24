# Hướng dẫn sử dụng `/gemini-chat`

## Tổng quan

`/gemini-chat` là endpoint stateful — AI nhớ toàn bộ lịch sử trò chuyện trong một session.

Mỗi session được định danh bằng `session_id`. Client phải tự lưu `session_id` từ response và gửi lại ở request tiếp theo để tiếp tục cuộc trò chuyện.

---

## Request

```
POST /gemini-chat
Content-Type: application/json
```

| Field        | Type   | Bắt buộc | Mô tả                                                               |
| ------------ | ------ | -------- | ------------------------------------------------------------------- |
| `message`    | string | Có       | Nội dung tin nhắn                                                   |
| `model`      | string | Không    | Model Gemini (mặc định: `gemini-3.0-flash`)                         |
| `session_id` | string | Không    | ID session để tiếp tục cuộc trò chuyện. Bỏ trống để tạo session mới |
| `files`      | array  | Không    | Danh sách đường dẫn file đính kèm                                   |

### Models hỗ trợ

- `gemini-3.0-flash` (mặc định)
- `gemini-3.0-pro`
- `gemini-3.0-flash-thinking`

---

## Response

```json
{
  "response": "Nội dung trả lời",
  "session_id": "uuid-của-session",
  "images": [...],
  "thoughts": "..."
}
```

| Field        | Mô tả                                                   |
| ------------ | ------------------------------------------------------- |
| `response`   | Nội dung trả lời từ AI                                  |
| `session_id` | ID session — lưu lại để dùng cho request tiếp theo      |
| `images`     | Danh sách ảnh (nếu có), chỉ xuất hiện khi AI trả về ảnh |
| `thoughts`   | Chuỗi suy nghĩ (chỉ có với model `flash-thinking`)      |

---

## Ví dụ

### Bước 1 — Bắt đầu cuộc trò chuyện (không cần session_id)

```bash
curl -X POST http://localhost:6969/gemini-chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tên tôi là Huy", "model": "gemini-3.0-flash"}'
```

Response:

```json
{
    "response": "Chào Huy! Rất vui được gặp bạn.",
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Bước 2 — Tiếp tục cuộc trò chuyện (gửi session_id)

```bash
curl -X POST http://localhost:6969/gemini-chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tên tôi là gì vậy?",
    "model": "gemini-3.0-flash",
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

Response:

```json
{
    "response": "Tên bạn là Huy.",
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

> `session_id` trả về luôn giống với `session_id` đã gửi vào.

### Bắt đầu cuộc trò chuyện mới

Không gửi `session_id` (hoặc gửi `null`) — server sẽ tạo session mới với ID khác.

```bash
curl -X POST http://localhost:6969/gemini-chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Xin chào!", "model": "gemini-3.0-flash"}'
```

---

## Ví dụ với Python

```python
import requests

BASE_URL = "http://localhost:6969"

def chat(message: str, session_id: str = None, model: str = "gemini-3.0-flash") -> dict:
    payload = {"message": message, "model": model}
    if session_id:
        payload["session_id"] = session_id

    res = requests.post(f"{BASE_URL}/gemini-chat", json=payload)
    res.raise_for_status()
    return res.json()


# Bắt đầu cuộc trò chuyện
reply = chat("Tên tôi là Huy")
session_id = reply["session_id"]
print(reply["response"])

# Tiếp tục
reply = chat("Tên tôi là gì?", session_id=session_id)
print(reply["response"])  # "Tên bạn là Huy."

# Tiếp tục
reply = chat("Hãy kể cho tôi nghe một câu chuyện ngắn", session_id=session_id)
print(reply["response"])
```

---

## Lưu ý

- **Session tồn tại trong RAM** — nếu server restart, toàn bộ session sẽ mất.
- **Mỗi session_id là độc lập** — nhiều client có thể chat song song mà không bị lẫn lộn.
- **Đổi model trong cùng session** sẽ bắt đầu một chat session Gemini mới (mất lịch sử trò chuyện với model cũ).
- **Không có cơ chế timeout** — session sẽ tồn tại cho đến khi server restart.

---

## So sánh với `/v1/chat/completions`

|                     | `/gemini-chat`              | `/v1/chat/completions`               |
| ------------------- | --------------------------- | ------------------------------------ |
| Lịch sử             | Server giữ qua `session_id` | Client tự gửi lại toàn bộ `messages` |
| Streaming           | Không                       | Có (`"stream": true`)                |
| Format              | Custom                      | OpenAI-compatible                    |
| Dùng với OpenAI SDK | Không                       | Có                                   |
