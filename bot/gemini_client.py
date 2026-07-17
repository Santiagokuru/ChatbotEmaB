from google import genai
from google.genai import types

from bot.config import GEMINI_API_KEY, GEMINI_MODEL
from bot.models import ClientInfo, ItemList

_client = genai.Client(api_key=GEMINI_API_KEY)


def _build_parts(text: str | None, audio: bytes | None, audio_mime: str) -> list[types.Part]:
    parts: list[types.Part] = []
    if audio:
        parts.append(types.Part.from_bytes(data=audio, mime_type=audio_mime))
    if text:
        parts.append(types.Part.from_text(text=text))
    return parts


def extract_client(text: str | None = None, audio: bytes | None = None, audio_mime: str = "audio/ogg") -> ClientInfo:
    prompt = (
        "El usuario está describiendo el cliente para una cotización (nombre y, si lo menciona, "
        "un dato de contacto como teléfono o email). Extraé esos datos. Si no menciona contacto, dejalo vacío."
    )
    parts = [types.Part.from_text(text=prompt)] + _build_parts(text, audio, audio_mime)
    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ClientInfo,
        ),
    )
    return ClientInfo.model_validate_json(response.text)


def extract_items(text: str | None = None, audio: bytes | None = None, audio_mime: str = "audio/ogg") -> ItemList:
    prompt = (
        "El usuario está describiendo uno o varios ítems (productos o servicios) para agregar a una cotización. "
        "Extraé cada ítem con su nombre, cantidad y precio unitario. Si no menciona cantidad, asumí 1. "
        "Los precios son números sin símbolo de moneda."
    )
    parts = [types.Part.from_text(text=prompt)] + _build_parts(text, audio, audio_mime)
    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ItemList,
        ),
    )
    return ItemList.model_validate_json(response.text)
