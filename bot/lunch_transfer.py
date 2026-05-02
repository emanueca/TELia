"""
Handlers para o sistema de transferência de almoço.
"""

import logging
from datetime import date
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from database.queries import (
    get_usuario,
    get_ru_credentials,
    add_to_lunch_queue,
    remove_from_lunch_queue,
    user_in_lunch_queue,
    create_lunch_transfer,
    get_lunch_queue_entries,
    find_matching_lunch_partner,
    update_transfer_status,
    get_pending_transfers_for_user,
)
from ru.booking import get_transferable_meals, transfer_lunch
from ru.credentials import decrypt

logger = logging.getLogger(__name__)


async def transferir_almoco(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /transferir_almoco - Menu inicial de transferência."""
    user_id = update.effective_user.id
    usuario = get_usuario(user_id)

    if not usuario:
        await update.message.reply_text(
            "❌ Você precisa estar logado para usar este comando.\n"
            "Use /login para entrar na sua conta."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("🍽️ Enviar Almoço", callback_data="lunch:send"),
            InlineKeyboardButton("📥 Receber Almoço", callback_data="lunch:receive"),
        ],
        [InlineKeyboardButton("❌ Cancelar", callback_data="lunch:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🍽️ **TRANSFERÊNCIA DE ALMOÇO**\n\n"
        "O que deseja fazer?",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def lunch_send_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia o fluxo de envio de almoço."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    usuario = get_usuario(user_id)

    if not usuario:
        await query.edit_message_text("❌ Usuário não encontrado.")
        return

    # Verifica se tem credenciais do RU
    creds = get_ru_credentials(user_id)

    if not creds:
        # Pede login no RU
        keyboard = [
            [InlineKeyboardButton("🔐 Fazer Login", callback_data="lunch:ru_login")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="lunch:cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔐 **LOGIN NO RU**\n\n"
            "Você precisa fazer login no RU para transferir almoço.\n"
            "Deseja continuar?",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        context.user_data["lunch_flow"] = "send"
        return

    # Se já tem credenciais, vai direto para escolher modo
    await _show_send_options(query, context)


async def _show_send_options(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra opções de envio: direto ou listão."""
    keyboard = [
        [InlineKeyboardButton("📤 Enviar Direto", callback_data="lunch:send_direct")],
        [InlineKeyboardButton("📋 Entrar no Listão", callback_data="lunch:send_queue")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="lunch:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🍽️ **ENVIAR ALMOÇO**\n\n"
        "Como deseja enviar?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    context.user_data["lunch_flow"] = "send_options"


async def lunch_send_direct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fluxo de envio direto: pedir CPF de destino."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "👤 **ENVIO DIRETO**\n\n"
        "Digite o CPF da pessoa que deseja enviar o almoço:"
    )
    context.user_data["lunch_flow"] = "send_direct_cpf"


async def lunch_send_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fluxo de entrada no listão como oferecedor."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # Verifica se já está no listão
    in_queue = user_in_lunch_queue(user_id)
    if in_queue:
        await query.edit_message_text(
            "ℹ️ Você já está no listão como "
            f"**{'oferecedor' if in_queue['mode'] == 'offering' else 'buscador'}**.\n\n"
            "Digite /transferir_almoco para sair do listão."
        )
        return

    # Pede tempo que quer ficar no listão
    keyboard = [
        [InlineKeyboardButton("24 horas", callback_data="lunch:queue_24h")],
        [InlineKeyboardButton("13 horas", callback_data="lunch:queue_13h")],
        [InlineKeyboardButton("5 horas", callback_data="lunch:queue_5h")],
        [InlineKeyboardButton("2 horas", callback_data="lunch:queue_2h")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="lunch:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "⏱️ **TEMPO NO LISTÃO**\n\n"
        "Quanto tempo você deseja ficar no listão?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    context.user_data["lunch_flow"] = "send_queue_time"


async def lunch_receive_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia o fluxo de recebimento de almoço."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    usuario = get_usuario(user_id)

    if not usuario:
        await query.edit_message_text("❌ Usuário não encontrado.")
        return

    # Verifica se tem credenciais do RU
    creds = get_ru_credentials(user_id)

    if not creds:
        keyboard = [
            [InlineKeyboardButton("🔐 Fazer Login", callback_data="lunch:ru_login")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="lunch:cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔐 **LOGIN NO RU**\n\n"
            "Você precisa fazer login no RU para receber almoço.\n"
            "Deseja continuar?",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        context.user_data["lunch_flow"] = "receive"
        return

    # Se já tem credenciais, vai para opções de recebimento
    await _show_receive_options(query, context)


async def _show_receive_options(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra opções de recebimento."""
    keyboard = [
        [InlineKeyboardButton("📋 Entrar no Listão", callback_data="lunch:receive_queue")],
        [InlineKeyboardButton("📥 Pendências", callback_data="lunch:receive_pending")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="lunch:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📥 **RECEBER ALMOÇO**\n\n"
        "Como deseja proceder?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    context.user_data["lunch_flow"] = "receive_options"


async def lunch_receive_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fluxo de entrada no listão como buscador."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # Verifica se já está no listão
    in_queue = user_in_lunch_queue(user_id)
    if in_queue:
        await query.edit_message_text(
            "ℹ️ Você já está no listão como "
            f"**{'oferecedor' if in_queue['mode'] == 'offering' else 'buscador'}**.\n\n"
            "Digite /transferir_almoco para sair do listão."
        )
        return

    # Pede tempo que quer ficar no listão
    keyboard = [
        [InlineKeyboardButton("24 horas", callback_data="lunch:receive_queue_24h")],
        [InlineKeyboardButton("13 horas", callback_data="lunch:receive_queue_13h")],
        [InlineKeyboardButton("5 horas", callback_data="lunch:receive_queue_5h")],
        [InlineKeyboardButton("2 horas", callback_data="lunch:receive_queue_2h")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="lunch:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "⏱️ **TEMPO NO LISTÃO**\n\n"
        "Quanto tempo você deseja ficar no listão?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    context.user_data["lunch_flow"] = "receive_queue_time"


async def lunch_queue_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa tempo no listão e adiciona à fila."""
    query = update.callback_query
    callback_data = query.data

    # Extrai o tempo (ex: "lunch:queue_24h" -> "24h")
    time_window = callback_data.split("_")[-1]

    user_id = update.effective_user.id
    usuario = get_usuario(user_id)
    creds = get_ru_credentials(user_id)

    if not creds:
        await query.answer("❌ Credenciais não encontradas", show_alert=True)
        return

    # Descriptografa CPF
    cpf = decrypt(creds["cpf_enc"])

    # Determina modo (offering ou seeking)
    flow = context.user_data.get("lunch_flow", "")
    mode = "offering" if "send" in flow else "seeking"

    # Adiciona ao listão
    success = add_to_lunch_queue(
        user_id=user_id,
        mode=mode,
        cpf=cpf,
        full_name=usuario.get("email", ""),  # email como fallback
        time_window=time_window,
    )

    if not success:
        await query.answer("❌ Erro ao entrar no listão", show_alert=True)
        return

    # Tenta fazer match
    partner = find_matching_lunch_partner(user_id)

    if partner:
        # Tem um parceiro! Cria notificação
        await query.edit_message_text(
            f"✅ **MATCH!**\n\n"
            f"Encontramos alguém para fazer a transferência com você!\n\n"
            f"Usuário: `{partner['cpf']}`\n"
            f"Modo: **{'Oferecedor' if partner['mode'] == 'offering' else 'Buscador'}**\n\n"
            f"Você será notificado em breve com os próximos passos.",
            parse_mode="Markdown",
        )

        # Aqui você criaria a notificação para o parceiro também
        # Por enquanto, apenas marca como entrado no listão
        context.user_data["lunch_match"] = partner
    else:
        await query.edit_message_text(
            f"✅ **ENTROU NO LISTÃO**\n\n"
            f"Modo: **{'Oferecedor' if mode == 'offering' else 'Buscador'}**\n"
            f"Tempo: **{time_window}**\n\n"
            f"Quando alguém compatível entrar, você receberá uma notificação aqui."
        )

    context.user_data["lunch_flow"] = ""


async def lunch_ru_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia fluxo de login no RU."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔐 **LOGIN NO RU**\n\n"
        "Digite seu CPF:"
    )
    context.user_data["lunch_flow"] = "ru_login_cpf"


async def lunch_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancela fluxo de transferência."""
    query = update.callback_query
    await query.answer()

    remove_from_lunch_queue(update.effective_user.id)

    await query.edit_message_text("❌ Operação cancelada.")
    context.user_data["lunch_flow"] = ""


async def lunch_receive_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra transferências pendentes para receber."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    pending = get_pending_transfers_for_user(user_id, direction='received')

    if not pending:
        await query.edit_message_text(
            "📭 Você não tem transferências pendentes.\n\n"
            "Quando alguém enviar almoço para você, aparecerá aqui."
        )
        return

    # Formata lista de pendências
    msg = "📋 **TRANSFERÊNCIAS PENDENTES**\n\n"
    for transfer in pending:
        msg += (
            f"📅 De: `{transfer['donor_cpf']}`\n"
            f"Data: {transfer['transfer_date']}\n"
            f"Status: {transfer['status']}\n\n"
        )

    keyboard = [[InlineKeyboardButton("❌ Voltar", callback_data="lunch:cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


# ── Funções de Suporte para Notificações ───────────────────────────────────

async def send_lunch_match_notification(app, donor_id: int, recipient_id: int) -> None:
    """Envia notificação de match para ambos os usuários."""
    try:
        # Notifica o doador
        message_donor = (
            "✅ **ALMOÇO ENCONTRADO!**\n\n"
            "Você foi pareado com alguém que quer receber seu almoço!\n\n"
            "Clique em 'Aceitar Match' para prosseguir com a transferência."
        )
        keyboard = [
            [InlineKeyboardButton("✅ Aceitar Match", callback_data=f"lunch:accept_match_{donor_id}")],
            [InlineKeyboardButton("❌ Recusar", callback_data=f"lunch:reject_match_{donor_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await app.bot.send_message(
            chat_id=donor_id,
            text=message_donor,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        # Notifica o receptor
        message_recipient = (
            "✅ **ALMOÇO ENCONTRADO!**\n\n"
            "Você foi pareado com alguém que tem almoço disponível!\n\n"
            "Clique em 'Aceitar Match' para prosseguir com a transferência."
        )
        await app.bot.send_message(
            chat_id=recipient_id,
            text=message_recipient,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de match: {e}")


async def send_transfer_notification(app, recipient_id: int, donor_id: int, transfer_id: int) -> None:
    """Envia notificação de transferência recebida."""
    try:
        donor = get_usuario(donor_id)
        donor_name = donor.get("email", "alguém") if donor else "alguém"

        message = (
            f"🍽️ **VOCÊ RECEBEU ALMOÇO!**\n\n"
            f"Doador: `{donor_name}`\n"
            f"Data: hoje\n\n"
            f"O que deseja fazer?"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Aceitar", callback_data=f"lunch:accept_{transfer_id}"),
                InlineKeyboardButton("❌ Recusar", callback_data=f"lunch:reject_{transfer_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await app.bot.send_message(
            chat_id=recipient_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de transferência: {e}")


# ── Processamento de Mensagens de Texto ────────────────────────────────────

async def handle_lunch_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de texto no fluxo de transferência de almoço."""
    flow = context.user_data.get("lunch_flow", "")

    if flow == "ru_login_cpf":
        # Recebeu CPF
        cpf = update.message.text.strip()
        if not cpf or len(cpf) < 10:
            await update.message.reply_text("❌ CPF inválido. Tente novamente:")
            return

        context.user_data["lunch_cpf"] = cpf
        context.user_data["lunch_flow"] = "ru_login_senha"
        await update.message.reply_text("🔐 Agora digite sua senha do RU:")

    elif flow == "ru_login_senha":
        # Recebeu senha
        senha = update.message.text.strip()
        if not senha:
            await update.message.reply_text("❌ Senha inválida. Tente novamente:")
            return

        cpf = context.user_data.get("lunch_cpf", "")
        user_id = update.effective_user.id

        # Tenta fazer login no RU
        from ru.credentials import encrypt
        from database.queries import save_ru_credentials

        try:
            # Tenta acessar os agendamentos para validar credenciais
            result = await get_transferable_meals(cpf, senha)

            if not result["success"]:
                await update.message.reply_text(
                    f"❌ Erro no login: {result['error']}\n"
                    "Tente novamente digitando /transferir_almoco"
                )
                context.user_data["lunch_flow"] = ""
                return

            # Salva credenciais criptografadas
            cpf_enc = encrypt(cpf)
            senha_enc = encrypt(senha)
            save_ru_credentials(user_id, cpf_enc, senha_enc)

            await update.message.reply_text("✅ Login bem-sucedido!")

            # Volta para o fluxo anterior
            original_flow = context.user_data.get("lunch_original_flow", "send")
            context.user_data["lunch_flow"] = ""

            if original_flow == "send":
                # Mostra opções de envio
                # Cria uma query fake para usar a função existente
                class FakeQuery:
                    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

                await _show_send_options(FakeQuery(), context)
            else:
                # Mostra opções de recebimento
                class FakeQuery:
                    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

                await _show_receive_options(FakeQuery(), context)

        except Exception as e:
            logger.error(f"Erro ao fazer login no RU: {e}")
            await update.message.reply_text(
                f"❌ Erro ao conectar com o RU: {str(e)}\n"
                "Tente novamente."
            )
            context.user_data["lunch_flow"] = ""

    elif flow == "send_direct_cpf":
        # Recebeu CPF de destino para envio direto
        destination_cpf = update.message.text.strip()
        if not destination_cpf or len(destination_cpf) < 10:
            await update.message.reply_text("❌ CPF inválido. Tente novamente:")
            return

        user_id = update.effective_user.id
        creds = get_ru_credentials(user_id)

        if not creds:
            await update.message.reply_text("❌ Credenciais não encontradas.")
            context.user_data["lunch_flow"] = ""
            return

        cpf = decrypt(creds["cpf_enc"])
        senha = decrypt(creds["senha_enc"])

        # Tenta fazer a transferência
        await update.message.reply_text("⏳ Processando transferência... Aguarde.")

        try:
            result = await transfer_lunch(cpf, senha, destination_cpf)

            if result["success"]:
                await update.message.reply_text(
                    f"✅ {result['message']}\n\n"
                    "Seu almoço foi transferido com sucesso!"
                )
            else:
                await update.message.reply_text(
                    f"❌ {result['error']}\n"
                    "Tente novamente ou use a opção 'Entrar no Listão'."
                )
        except Exception as e:
            logger.error(f"Erro ao transferir almoço: {e}")
            await update.message.reply_text(
                f"❌ Erro ao processar transferência: {str(e)}"
            )

        context.user_data["lunch_flow"] = ""

