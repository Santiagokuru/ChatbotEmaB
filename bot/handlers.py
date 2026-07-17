from bot import db, state, telegram_client as tg
from bot.config import BUSINESS
from bot.gemini_client import extract_client, extract_items
from bot.models import Item, QuoteData
from bot.pdf import build_quote_pdf


def _incoming_content(message: dict) -> tuple[str | None, bytes | None, str]:
    """Devuelve (texto, audio_bytes, audio_mime) a partir de un mensaje de Telegram."""
    if "voice" in message:
        audio = tg.download_file(message["voice"]["file_id"])
        return None, audio, message["voice"].get("mime_type", "audio/ogg")
    if "audio" in message:
        audio = tg.download_file(message["audio"]["file_id"])
        return None, audio, message["audio"].get("mime_type", "audio/ogg")
    return message.get("text"), None, "audio/ogg"


def handle_message(message: dict) -> None:
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text.startswith("/start") or text.startswith("/nueva"):
        state.save_session(chat_id, state.AWAITING_CLIENT, QuoteData())
        tg.send_message(chat_id, "Arrancamos una cotización nueva. Contame quién es el cliente (nombre y contacto si tenés).")
        return

    if text.startswith("/cancelar"):
        state.clear_session(chat_id)
        tg.send_message(chat_id, "Cotización cancelada.")
        return

    if text.startswith("/historial"):
        _send_history(chat_id)
        return

    if text.startswith("/listo"):
        _handle_listo(chat_id)
        return

    current_state, data = state.get_session(chat_id)

    if current_state == state.AWAITING_CLIENT:
        _handle_client_message(chat_id, message, data)
        return

    if current_state == state.AWAITING_ITEMS:
        _handle_items_message(chat_id, message, data)
        return

    tg.send_message(chat_id, "Escribí /nueva para empezar una cotización o /historial para ver las anteriores.")


def _handle_client_message(chat_id: int, message: dict, data: QuoteData) -> None:
    text, audio, audio_mime = _incoming_content(message)
    if not text and not audio:
        tg.send_message(chat_id, "Contame el nombre del cliente en texto o audio.")
        return

    client = extract_client(text=text, audio=audio, audio_mime=audio_mime)
    data.client = client
    state.save_session(chat_id, state.AWAITING_ITEMS, data)
    tg.send_message(
        chat_id,
        f"Cliente: <b>{client.name}</b>. Ahora contame los ítems (producto, cantidad y precio). "
        "Podés mandarlos todos juntos o de a uno. Cuando termines, escribí /listo.",
    )


def _handle_items_message(chat_id: int, message: dict, data: QuoteData) -> None:
    text, audio, audio_mime = _incoming_content(message)
    if not text and not audio:
        tg.send_message(chat_id, "Contame los ítems en texto o audio, o escribí /listo para terminar.")
        return

    result = extract_items(text=text, audio=audio, audio_mime=audio_mime)
    if not result.items:
        tg.send_message(chat_id, "No pude identificar ítems ahí. Probá de nuevo, por ejemplo: '3 sillas a $50'.")
        return

    data.items.extend(result.items)
    state.save_session(chat_id, state.AWAITING_ITEMS, data)

    added = ", ".join(f"{i.quantity:g} x {i.name} (${i.subtotal:,.2f})" for i in result.items)
    tg.send_message(
        chat_id,
        f"Agregado: {added}.\nLlevás {len(data.items)} ítem(s), total parcial ${data.total:,.2f}. "
        "Seguí agregando o escribí /listo.",
    )


def _handle_listo(chat_id: int) -> None:
    current_state, data = state.get_session(chat_id)
    if current_state != state.AWAITING_ITEMS or not data.items:
        tg.send_message(chat_id, "Todavía no hay ítems cargados. Escribí /nueva para empezar.")
        return

    state.save_session(chat_id, state.CONFIRMING, data)
    lines = [f"{i.quantity:g} x {i.name} — ${i.subtotal:,.2f}" for i in data.items]
    summary = "\n".join(lines)
    tg.send_message(
        chat_id,
        f"<b>Resumen para {data.client.name}</b>\n{summary}\n\n<b>Total: ${data.total:,.2f}</b>",
        reply_markup=tg.inline_keyboard([[("Confirmar", "confirm"), ("Cancelar", "cancel")]]),
    )


def handle_callback_query(callback_query: dict) -> None:
    chat_id = callback_query["message"]["chat"]["id"]
    action = callback_query["data"]
    tg.answer_callback_query(callback_query["id"])

    if action == "confirm":
        _confirm_quote(chat_id)
        return

    if action == "cancel":
        state.clear_session(chat_id)
        tg.send_message(chat_id, "Cotización cancelada.")
        return

    if action.startswith("history:"):
        quote_id = action.split(":", 1)[1]
        _resend_quote(chat_id, quote_id)


def _confirm_quote(chat_id: int) -> None:
    current_state, data = state.get_session(chat_id)
    if current_state != state.CONFIRMING or not data.client or not data.items:
        tg.send_message(chat_id, "No hay una cotización pendiente de confirmar.")
        return

    pdf_bytes = build_quote_pdf(BUSINESS, data.client, data.items, data.total)
    filename = f"cotizacion_{data.client.name.replace(' ', '_')}.pdf"
    tg.send_document(chat_id, filename, pdf_bytes, caption=f"Cotización para {data.client.name}")

    db.save_quote(chat_id, data.client, data.items, data.total)
    state.clear_session(chat_id)


def _send_history(chat_id: int) -> None:
    quotes = db.list_quotes(chat_id)
    if not quotes:
        tg.send_message(chat_id, "Todavía no generaste ninguna cotización.")
        return

    buttons = [
        [(f"{q['client']['name']} — ${q['total']:,.2f} ({q['created_at'][:10]})", f"history:{q['id']}")]
        for q in quotes
    ]
    tg.send_message(chat_id, "Últimas cotizaciones:", reply_markup=tg.inline_keyboard(buttons))


def _resend_quote(chat_id: int, quote_id: str) -> None:
    quote = db.get_quote(quote_id)
    if not quote:
        tg.send_message(chat_id, "No encontré esa cotización.")
        return

    client = QuoteData.model_validate({"client": quote["client"], "items": quote["items"]}).client
    items = [Item.model_validate(i) for i in quote["items"]]
    pdf_bytes = build_quote_pdf(BUSINESS, client, items, quote["total"])
    filename = f"cotizacion_{client.name.replace(' ', '_')}.pdf"
    tg.send_document(chat_id, filename, pdf_bytes, caption=f"Cotización para {client.name}")
