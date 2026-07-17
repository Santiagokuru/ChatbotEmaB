from bot.db import get_client
from bot.models import QuoteData

IDLE = "idle"
COLLECTING = "collecting"
CONFIRMING = "confirming"


def get_session(chat_id: int) -> tuple[str, QuoteData]:
    resp = get_client().table("sessions").select("state, data").eq("chat_id", chat_id).limit(1).execute()
    if not resp.data:
        return IDLE, QuoteData()
    row = resp.data[0]
    return row["state"], QuoteData.model_validate(row["data"])


def save_session(chat_id: int, state: str, data: QuoteData) -> None:
    get_client().table("sessions").upsert(
        {"chat_id": chat_id, "state": state, "data": data.model_dump(mode="json")}
    ).execute()


def clear_session(chat_id: int) -> None:
    get_client().table("sessions").delete().eq("chat_id", chat_id).execute()
