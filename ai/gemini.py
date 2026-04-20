import os
import json
import logging
import math
import re
from datetime import datetime
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, NotFound
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
_model_cache: dict[str, genai.GenerativeModel] = {}
logger = logging.getLogger(__name__)

_ALLOWED_MODELS = {
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash-lite",
}

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


def _get_selected_model(profile: dict) -> str:
    profile_model = str((profile or {}).get("ai_model") or "").strip()
    if profile_model in _ALLOWED_MODELS:
        return profile_model
    if DEFAULT_MODEL in _ALLOWED_MODELS:
        return DEFAULT_MODEL
    return "gemini-2.0-flash"


def _get_model(model_name: str) -> genai.GenerativeModel:
    if model_name not in _model_cache:
        _model_cache[model_name] = genai.GenerativeModel(model_name)
    return _model_cache[model_name]


def _extract_retry_seconds(exc: Exception) -> int | None:
    message = str(exc)
    match = re.search(r"Please retry in\s+([0-9]+(?:\.[0-9]+)?)s", message)
    if match:
        return max(1, math.ceil(float(match.group(1))))
    match = re.search(r"retry_delay\s*\{\s*seconds:\s*([0-9]+)", message)
    if match:
        return max(1, int(match.group(1)))
    return None


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

        selected_model = _get_selected_model(profile)
        response = _get_model(selected_model).generate_content(prompt)
        raw = response.text or ""

        if not raw:
            raise ValueError("resposta vazia do Gemini")

        result = _extract_json_object(raw)

        return {
            "reply": str(result.get("reply") or "Desculpe, não entendi."),
            "reminder": result.get("reminder") if isinstance(result.get("reminder"), dict) else None,
            "profile_updates": result.get("profile_updates") or [],
        }
    except ResourceExhausted as exc:
        logger.warning("Cota da API Gemini esgotada: %s", exc)
        retry_seconds = _extract_retry_seconds(exc)
        if retry_seconds:
            retry_minutes = max(1, math.ceil(retry_seconds / 60))
            wait_hint = (
                f"⚠️ A cota da IA esta no limite. Espere cerca de {retry_minutes} min "
                f"({retry_seconds}s) para tentar novamente."
            )
        else:
            wait_hint = "⚠️ A cota da IA esta no limite. Espere alguns minutos para tentar novamente."
        return {
            "reply": wait_hint,
            "reminder": None,
            "profile_updates": [],
        }
    except NotFound:
        logger.exception("Modelo Gemini indisponível para esta chave/projeto.")
        return {
            "reply": "⚠️ O modelo Gemini configurado não está disponível para esta chave. Ajuste a variável GEMINI_MODEL para um modelo habilitado.",
            "reminder": None,
            "profile_updates": [],
        }
    except Exception:
        logger.exception("Falha ao processar mensagem com Gemini.")
        return {
            "reply": "⚠️ Tive um problema interno. Tente novamente ou contate um adiministrador...",
            "reminder": None,
            "profile_updates": [],
        }
