import json
from datetime import datetime
from pathlib import Path

QUARENTENA_PATH = Path(__file__).resolve().parents[1] / "treino_quarentena.jsonl"


def salvar_treino_quarentena(pergunta: str, resposta: str, metadata: dict | None = None) -> None:
    """Salva um par (pergunta, resposta) em formato JSONL na quarentena.

    Cada linha é um JSON com campos: pergunta, resposta, timestamp, metadata.
    """
    entry = {
        "pergunta": pergunta or "",
        "resposta": resposta or "",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata or {},
    }
    try:
        QUARENTENA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QUARENTENA_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Não propaga exceções para não quebrar o loop do bot; o caller pode logar falhas.
        raise
