from supabase import Client, create_client

from bot.config import SUPABASE_KEY, SUPABASE_URL, HISTORY_PAGE_SIZE
from bot.models import ClientInfo, Item

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def save_quote(
    chat_id: int, client: ClientInfo, items: list[Item], total: float, estimated_time: str
) -> int:
    resp = (
        get_client()
        .table("quotes")
        .insert(
            {
                "chat_id": chat_id,
                "client": client.model_dump(),
                "items": [item.model_dump() for item in items],
                "total": total,
                "estimated_time": estimated_time,
            }
        )
        .execute()
    )
    return resp.data[0]["quote_number"]


def list_quotes(chat_id: int, limit: int = HISTORY_PAGE_SIZE) -> list[dict]:
    resp = (
        get_client()
        .table("quotes")
        .select("id, client, total, created_at")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data


def get_quote(quote_id: str) -> dict | None:
    resp = get_client().table("quotes").select("*").eq("id", quote_id).limit(1).execute()
    return resp.data[0] if resp.data else None
