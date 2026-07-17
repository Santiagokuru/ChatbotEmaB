import httpx

from bot.config import TELEGRAM_BOT_TOKEN

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
FILE_BASE = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"


def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    with httpx.Client(timeout=15) as client:
        client.post(f"{API_BASE}/sendMessage", json=payload)


def send_document(chat_id: int, filename: str, content: bytes, caption: str = "") -> None:
    with httpx.Client(timeout=30) as client:
        client.post(
            f"{API_BASE}/sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (filename, content, "application/pdf")},
        )


def answer_callback_query(callback_query_id: str) -> None:
    with httpx.Client(timeout=15) as client:
        client.post(f"{API_BASE}/answerCallbackQuery", json={"callback_query_id": callback_query_id})


def download_file(file_id: str) -> bytes:
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{API_BASE}/getFile", params={"file_id": file_id})
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]
        file_resp = client.get(f"{FILE_BASE}/{file_path}")
        file_resp.raise_for_status()
        return file_resp.content


def inline_keyboard(buttons: list[list[tuple[str, str]]]) -> dict:
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": data} for text, data in row] for row in buttons
        ]
    }
