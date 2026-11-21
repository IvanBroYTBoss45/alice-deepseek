import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI()

API_KEY = os.environ.get("ORCA_API_KEY", "").strip()
MODEL = "deepseek/deepseek-v4-flash-free"

sessions = {}

SYSTEM_PROMPT = (
    "Ты — китайский брат Алисы по имени Дипсик. Общайся как свой пацан, "
    "на ты, без официоза, коротко и по делу (максимум 2-3 предложения), "
    "потому что твой ответ будет зачитываться голосом в умной колонке. "
    "Не используй смайлики, звездочки и разметку текста."
)

@app.post("/{full_path:path}")
async def alice_webhook(request: Request, full_path: str = ""):
    data = await request.json()
    session_id = data.get("session", {}).get("session_id", "default")
    user_text = data.get("request", {}).get("original_utterance", "").strip()
    is_new = data.get("session", {}).get("new", False)

    if is_new and not user_text:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        return make_response("Здарова! Китайский брат на связи. Чё хотел?", False)

    if user_text.lower() in ["хватит", "выход", "пока", "стоп", "закройся"]:
        sessions.pop(session_id, None)
        return make_response("Бывай, бро! Если чё — зови.", True)

    if not API_KEY:
        return make_response("Бро, ключ ORCA_API_KEY пустой! Добавь его в Vercel и сделай Redeploy.", False)

    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    sessions[session_id].append({"role": "user", "content": user_text})
    history = [sessions[session_id][0]] + sessions[session_id][-6:]

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                "https://api.orcarouter.ai/v1/chat/completions",
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
            if resp.status_code != 200:
                return make_response(f"OrcaRouter отбил код {resp.status_code}: {resp.text[:80]}", False)

            result = resp.json()
            reply = result["choices"][0]["message"]["content"].strip()
            sessions[session_id].append({"role": "assistant", "content": reply})
            return make_response(reply, False)

    except httpx.TimeoutException:
        return make_response("Бро, Китай думает дольше 4 секунд. Спроси покороче!", False)
    except Exception as e:
        return make_response(f"Ошибка: {str(e)[:80]}", False)


def make_response(text: str, end_session: bool):
    return {
        "response": {
            "text": text,
            "tts": text,
            "end_session": end_session,
        },
        "version": "1.0",
    }
