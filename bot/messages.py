import hashlib
from telegram import Update
from telegram.ext import ContextTypes

from bot.commands import MSG_GITHUB
from database.queries import get_usuario, criar_usuario, save_reminder
from ai.gemini import extract_reminder


def gerar_hash_senha(senha_plana: str) -> str:
    return hashlib.sha256(senha_plana.encode("utf-8")).hexdigest()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # ── Fluxo de cadastro ─────────────────────────────────
    if text.startswith("E-mail:") and "Senha:" in text:
        await _processar_cadastro(update, chat_id, text)
        return

    # ── Barreira de acesso ────────────────────────────────
    usuario = get_usuario(chat_id)
    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "⚠️ Você precisa ter uma conta para usar a TELia.\n"
            "Digite /cadastrar para criar uma conta ou /login para entrar."
            + MSG_GITHUB
        )
        return

    # ── Lógica principal: extração de lembrete via IA ─────
    result = extract_reminder(text)

    if not result:
        await update.message.reply_text(
            "Não consegui identificar um lembrete. Tente algo como:\n"
            "_'Me lembra de X amanhã às 10h'_",
            parse_mode="Markdown",
        )
        return

    save_reminder(chat_id, result["message"], result["remind_at"])
    await update.message.reply_text(
        f"✅ Lembrete salvo! Vou te avisar sobre *{result['message']}* em `{result['remind_at']}`.",
        parse_mode="Markdown",
    )

async def _processar_cadastro(update: Update, chat_id: int, text: str):
    try:
        linhas = text.split("\n")
        email = linhas[0].split(":", 1)[1].strip()
        senha_plana = linhas[1].split(":", 1)[1].strip()

        if not email or not senha_plana:
            raise ValueError("campos vazios")

        senha_hash = gerar_hash_senha(senha_plana)
        criar_usuario(chat_id, email, senha_hash)

        await update.message.reply_text(
            "✅ Cadastro realizado com sucesso! Já pode me pedir lembretes." + MSG_GITHUB
        )
    except Exception:
        await update.message.reply_text(
            "❌ Formato inválido. Copie exatamente como mostrado e preencha:\n\n"
            "E-mail: seuemail@exemplo.com\nSenha: suasenha"
        )
