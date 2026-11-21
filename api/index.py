import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI()

API_KEY = os.environ.get("ORCA_API_KEY", "")
MODEL = "deepseek/deepseek-v4-flash-free"

# Храним историю диалога по ID сессии в оперативке
sessions = {}

SYSTEM_PROMPT = (
    "Ты — китайский брат Алисы по имени Дипсик. Общайся как свой пацан, "
    "на ты, без официоза, коротко и по делу (максимум 2-3 предложения), "
    "потому что твой ответ будет зачитываться голосом в умной колонке. "
    "Не используй смайлики, звездочки и разметку текста."
)

@app.post("/webhook")
@app.post("/")
async def alice_webhook(request: Request):
    data = await request.json()
    session_id = data["session"]["session_id"]
    user_text = data["request"].get("original_utterance", "").strip()
    is_new = data["session"].get("new", False)

    # Приветствие при запуске навыка
    if is_new and not user_text:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        return make_response("Здарова! Китайский брат на связи. Чё хотел?", False)

    # Команда выхода из навыка
    if user_text.lower() in ["хватит", "выход", "пока", "стоп", "закройся"]:
        sessions.pop(session_id, None)
        return make_response("Бывай, бро! Если чё — зови.", True)

    # Инициализация истории, если сессия новая, но сразу с вопросом
    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    sessions[session_id].append({"role": "user", "content": user_text})
    # Оставляем системный промпт + последние 6 сообщений, чтобы не тупило
    history = [sessions[session_id][0]] + sessions[session_id][-6:]

    try:
        async with httpx.AsyncClient(timeout=3.8) as client:
            resp = await client.post(
                "https://orcarouter.ai",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": history,
                    "max_tokens": 250,
                    "temperature": 0.7,
                },
            )
            result = resp.json()
            reply = result["choices"][0]["message"]["content"].strip()
            sessions[session_id].append({"role": "assistant", "content": reply})
            return make_response(reply, False)

    except httpx.TimeoutException:
        return make_response("Бро, сервер чёт задумался дольше 3 секунд. Повтори вопрос покороче!", False)
    except Exception:
        return make_response("Чёт связь с Китаем оборвалась, попробуй ещё раз.", False)


def make_response(text: str, end_session: bool):
    return {
        "response": {
            "text": text,
            "tts": text,
            "end_session": end_session,
        },
        "version": "1.0",
    }
