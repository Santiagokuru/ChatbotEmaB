import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")

GEMINI_API_KEY = _require("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

SUPABASE_URL = _require("SUPABASE_URL")
SUPABASE_KEY = _require("SUPABASE_KEY")

BUSINESS = {
    "name": os.environ.get("BUSINESS_NAME", ""),
    "phone": os.environ.get("BUSINESS_PHONE", ""),
    "email": os.environ.get("BUSINESS_EMAIL", ""),
    "address": os.environ.get("BUSINESS_ADDRESS", ""),
}

HISTORY_PAGE_SIZE = 10
