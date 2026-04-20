import os
import json
import logging
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
_model = genai.GenerativeModel("gemini-1.5-flash")
logger = logging.getLogger(__name__)

_PROMPT = """
Você é um extrator de lembretes. A partir da mensagem do usuário, extraia:
- "message": o que precisa ser lembrado (resumo curto)
- "remind_at": data e hora no formato ISO 8601 (ex: 2026-04-20T10:00:00)

Data e hora atual: {now}

Responda APENAS com JSON válido, sem markdown. Exemplo:
{{"message": "ligar pro João", "remind_at": "2026-04-20T10:00:00"}}

Se não for possível identificar um lembrete, responda: null

Mensagem do usuário: {user_message}
"""

def extract_reminder(user_message: str) -> dict | None:
    try:
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        prompt = _PROMPT.format(now=now, user_message=user_message)

        response = _model.generate_content(prompt)
        raw = (response.text or "").strip()

        if raw.startswith("```json"):
            raw = raw.replace("```json", "", 1)
        if raw.startswith("```"):
            raw = raw.replace("```", "", 1)
        if raw.endswith("```"):
            raw = raw[::-1].replace("```", "", 1)[::-1]

        raw = raw.strip()

        if not raw or raw.lower() == "null":
            return None

        return json.loads(raw)
    except Exception:
        logger.exception("Falha ao processar resposta do Gemini.")
        return None
