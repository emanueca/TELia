import os

import httpx


async def send_anonymous_to_brain(text: str, timeout: float = 25.0) -> str | None:
    """Envia texto ao servidor anônimo externo e retorna a resposta textual."""
    url = os.getenv("ANON_IA_URL")
    if not url:
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json={"text": text})
            if resp.status_code != 200:
                return None

            try:
                data = resp.json()
            except Exception:
                text_reply = (resp.text or "").strip()
                return text_reply or None

            if isinstance(data, dict):
                reply = data.get("reply")
                if isinstance(reply, str) and reply.strip():
                    return reply.strip()

                text_reply = data.get("text")
                if isinstance(text_reply, str) and text_reply.strip():
                    return text_reply.strip()

            return None
    except Exception:
        return None
