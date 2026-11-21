import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI()

API_KEY = os.environ.get("ORCA_API_KEY", "")
MODEL = "deepseek/deepseek-v4-flash-free"

sessions = {}

SYSTEM_PROMPT = (
    "Ты — китайский брат Алисы по имени Дипсик. Общайся как свой пацан, "
    "на ты, без официоза, коротко и по делу (максимум 2-3 предложения), "
    "потому что твой ответ будет зачитываться голосом в умной колонке. "
    "Не используй смайлики, звездочки и разметку текста."
)

@app.get("/")
async def healthcheck():
    return {"status": "ok"}

@app.post("/{full_path:path}")
async def alice_webhook(request: Request, full_path: str = ""):
    try:
        data = await request.json()
    except Exception:
        return make_response("Не понял запрос, бро.", False)

    session_id = data.get("session", {}).get("session_id", "default")
    user_text = data.get("request", {}).get("original_utterance", "").strip()
    is_new = data.get("session", {}).get("new", False)

    # Приветствие при запуске навыка
    if is_new and not user_text:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        return make_response("Здарова! Китайский брат на связи. Чё хотел?", False)

    # Команда выхода из навыка
    if user_text.lower() in ["хватит", "выход", "пока", "стоп", "закройся"]:
        sessions.pop(session_id, None)
        return make_response("Бывай, бро! Если чё — зови.", True)

    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    sessions[session_id].append({"role": "user", "content": user_text})
    history = [sessions[session_id][0]] + sessions[session_id][-6:]

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
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
        return make_response("Бро, сервер чёт задумался дольше 4 секунд. Спроси покороче!", False)
    except Exception as e:
        return make_response(f"Чёт сломалось на связи с Китаем: {str(e)[:60]}", False)


def make_response(text: str, end_session: bool):
    return {
        "response": {
            "text": text,
            "tts": text,
            "end_session": end_session,
        },
        "version": "1.0",
    }
