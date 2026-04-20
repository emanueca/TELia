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

_PROMPT = """Você é a TELia, uma assistente pessoal no Telegram. Responda sempre em português brasileiro, de forma natural e amigável.

Você pode:
1. Conversar livremente e responder perguntas gerais
2. Criar lembretes quando o usuário pedir
3. Lembrar de informações pessoais que o usuário compartilhar

Data e hora atual: {now}

Perfil do usuário (informações salvas):
{profile}

Histórico recente da conversa:
{history}

Analise a mensagem do usuário e responda em JSON com este formato exato:
{{
  "reply": "sua resposta para o usuário",
  "reminder": null,
  "profile_updates": []
}}

Regras:
- "reply": sempre preencha com sua resposta natural
- "reminder": preencha APENAS se o usuário pedir para ser lembrado de algo. Formato: {{"message": "o que lembrar", "remind_at": "YYYY-MM-DDTHH:MM:SS"}}
- "profile_updates": lista de {{"key": "chave", "value": "valor"}} com informações pessoais detectadas. Exemplos:
  - "meu nome é João" → [{{"key": "nome", "value": "João"}}]
  - "trabalho como médico" → [{{"key": "profissão", "value": "médico"}}]
  - "moro em SP" → [{{"key": "cidade", "value": "São Paulo"}}]
  - Se nenhuma info pessoal → []

Use o perfil e histórico para personalizar a resposta quando relevante.
Responda APENAS com JSON válido, sem markdown nem texto fora do JSON.

Mensagem do usuário: {user_message}"""


def _format_history(history: list[dict]) -> str:
    if not history:
        return "(sem histórico)"
    lines = []
    for msg in history:
        label = "Usuário" if msg["role"] == "user" else "TELia"
        lines.append(f"{label}: {msg['content']}")
    return "\n".join(lines)


def _format_profile(profile: dict) -> str:
    if not profile:
        return "(sem informações salvas)"
    return "\n".join(f"- {k}: {v}" for k, v in profile.items())


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()


def _extract_json_object(raw: str) -> dict:
    """Tries direct parse first, then extracts the outermost JSON object."""
    cleaned = _clean_json(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Resposta sem JSON válido")
        return json.loads(cleaned[start : end + 1])


def process_message(
    user_message: str,
    history: list[dict],
    profile: dict,
) -> dict:
    """
    Returns:
      {
        "reply": str,
        "reminder": {"message": str, "remind_at": str} | None,
        "profile_updates": [{"key": str, "value": str}]
      }
    """
    try:
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY não configurada")

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        prompt = _PROMPT.format(
            now=now,
            profile=_format_profile(profile),
            history=_format_history(history),
            user_message=user_message,
        )

        response = _model.generate_content(prompt)
        raw = response.text or ""

        if not raw:
            raise ValueError("resposta vazia do Gemini")

        result = _extract_json_object(raw)

        return {
            "reply": str(result.get("reply") or "Desculpe, não entendi."),
            "reminder": result.get("reminder") if isinstance(result.get("reminder"), dict) else None,
            "profile_updates": result.get("profile_updates") or [],
        }
    except Exception:
        logger.exception("Falha ao processar mensagem com Gemini.")
        return {
            "reply": "⚠️ Tive um problema interno. Tente novamente ou contate um adiministrador...",
            "reminder": None,
            "profile_updates": [],
        }
