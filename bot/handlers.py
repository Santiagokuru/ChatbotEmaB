from bot import agent, db, state, telegram_client as tg
from bot.config import BUSINESS
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


def _is_complete(data: QuoteData) -> bool:
    return bool(data.client and data.client.name) and bool(data.items) and all(
        i.unit_price > 0 for i in data.items
    )


def handle_message(message: dict) -> None:
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text.startswith("/start") or text.startswith("/nueva"):
        state.clear_session(chat_id)
        tg.send_message(
            chat_id,
            "Arrancamos una cotización nueva. Contame quién es el cliente y qué ítems querés cotizar "
            "(podés mandar todo junto, en texto o audio).",
        )
        return

    if text.startswith("/cancelar"):
        state.clear_session(chat_id)
        tg.send_message(chat_id, "Cotización cancelada.")
        return

    if text.startswith("/historial"):
        _send_history(chat_id)
        return

    current_state, data = state.get_session(chat_id)

    # Si llega texto nuevo mientras se esperaba la confirmación por botón,
    # lo tratamos como una corrección y volvemos a recolectar datos.
    if current_state == state.CONFIRMING:
        current_state = state.COLLECTING

    _handle_collecting_message(chat_id, message, data)


def _handle_collecting_message(chat_id: int, message: dict, data: QuoteData) -> None:
    text, audio, audio_mime = _incoming_content(message)
    if not text and not audio:
        tg.send_message(chat_id, "Contame en texto o audio los datos de la cotización.")
        return

    result = agent.run_turn(data, text=text, audio=audio, audio_mime=audio_mime)
    data = result.data

    if _is_complete(data):
        state.save_session(chat_id, state.CONFIRMING, data)
        _send_confirmation_summary(chat_id, data, extra_text=result.reply)
    else:
        state.save_session(chat_id, state.COLLECTING, data)
        tg.send_message(chat_id, result.reply or "Contame más detalles para armar la cotización.")


def _send_confirmation_summary(chat_id: int, data: QuoteData, extra_text: str = "") -> None:
    lines = [f"{i.quantity:g} x {i.name} — ${i.subtotal:,.2f}" for i in data.items]
    summary = "\n".join(lines)
    prefix = f"{extra_text}\n\n" if extra_text else ""
    tg.send_message(
        chat_id,
        f"{prefix}<b>Resumen para {data.client.name}</b>\n{summary}\n\n<b>Total: ${data.total:,.2f}</b>",
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
