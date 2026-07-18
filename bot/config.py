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
    "bank_account": os.environ.get("BUSINESS_BANK_ACCOUNT", ""),
    "bank_alias": os.environ.get("BUSINESS_ALIAS", ""),
    "signature": os.environ.get("BUSINESS_SIGNATURE", ""),
    "logo_path": os.environ.get("BUSINESS_LOGO_PATH", "src/assets/img/logo encabezado.png"),
    "validity_days": int(os.environ.get("BUSINESS_VALIDITY_DAYS", "15")),
    "quote_prefix": os.environ.get("BUSINESS_QUOTE_PREFIX", "002"),
}

HISTORY_PAGE_SIZE = 10
