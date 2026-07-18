from google import genai
from google.genai import types

from bot.config import GEMINI_API_KEY, GEMINI_MODEL
from bot.models import ClientInfo, Item, QuoteData

_client = genai.Client(api_key=GEMINI_API_KEY)

_MAX_TOOL_ROUNDS = 4

_SYSTEM_INSTRUCTION = (
    "Sos el asistente de un negocio que arma cotizaciones por Telegram. "
    "El usuario te va a describir, en uno o varios mensajes, quién es el cliente, qué ítems "
    "(productos o servicios) quiere cotizar (con su cantidad y precio unitario), y el tiempo estimado "
    "de realización del trabajo (ej. \"1 día\", \"2 días aprox\").\n\n"
    "Reflejá cada dato nuevo o cada corrección usando las herramientas disponibles "
    "(set_client, add_item, update_item, remove_item, set_estimated_time) — nunca respondas los datos solo "
    "en texto, siempre aplicalos con la herramienta correspondiente.\n\n"
    "Los ítems ya cargados se te muestran con su índice de posición (empezando en 0); usá ese índice "
    "para update_item y remove_item cuando el usuario corrija o borre uno.\n\n"
    "Después de aplicar los cambios, respondé en texto natural y breve:\n"
    "- Si todavía falta el nombre del cliente, el precio de algún ítem, o el tiempo estimado de "
    "realización, pedí puntualmente eso que falta.\n"
    "- Si ya está todo completo (cliente con nombre, todos los ítems con precio, tiempo estimado cargado), "
    "decilo para que el usuario sepa que puede confirmar.\n"
    "- Si el mensaje del usuario no tiene nada que ver con armar una cotización (un saludo, una pregunta "
    "general), no llames ninguna herramienta y respondé brevemente explicando que podés armar una cotización "
    "si te cuenta el cliente, los ítems y el tiempo estimado."
)

_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="set_client",
            description="Establece o actualiza los datos del cliente de la cotización.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "name": types.Schema(type="STRING", description="Nombre del cliente."),
                    "contact": types.Schema(
                        type="STRING", description="Teléfono o email del cliente, si lo mencionó."
                    ),
                },
                required=["name"],
            ),
        ),
        types.FunctionDeclaration(
            name="add_item",
            description="Agrega un ítem nuevo a la cotización.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "name": types.Schema(type="STRING", description="Nombre del producto o servicio."),
                    "quantity": types.Schema(
                        type="NUMBER", description="Cantidad. Si no se menciona, usar 1."
                    ),
                    "unit_price": types.Schema(
                        type="NUMBER", description="Precio unitario, sin símbolo de moneda."
                    ),
                },
                required=["name", "quantity"],
            ),
        ),
        types.FunctionDeclaration(
            name="update_item",
            description=(
                "Corrige un ítem ya cargado (nombre, cantidad y/o precio), identificado por su índice "
                "de posición."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "index": types.Schema(
                        type="INTEGER", description="Índice de posición del ítem a corregir (empieza en 0)."
                    ),
                    "name": types.Schema(type="STRING", description="Nuevo nombre, si cambia."),
                    "quantity": types.Schema(type="NUMBER", description="Nueva cantidad, si cambia."),
                    "unit_price": types.Schema(type="NUMBER", description="Nuevo precio unitario, si cambia."),
                },
                required=["index"],
            ),
        ),
        types.FunctionDeclaration(
            name="remove_item",
            description="Elimina un ítem ya cargado, identificado por su índice de posición.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "index": types.Schema(
                        type="INTEGER", description="Índice de posición del ítem a borrar (empieza en 0)."
                    ),
                },
                required=["index"],
            ),
        ),
        types.FunctionDeclaration(
            name="set_estimated_time",
            description="Establece el tiempo estimado de realización del trabajo (ej. '1 día', '2 días aprox').",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "estimated_time": types.Schema(
                        type="STRING", description="Tiempo estimado de realización, tal como lo dijo el usuario."
                    ),
                },
                required=["estimated_time"],
            ),
        ),
    ]
)


class AgentResult:
    def __init__(self, data: QuoteData, reply: str):
        self.data = data
        self.reply = reply


def _apply_tool_call(data: QuoteData, name: str, args: dict) -> str | None:
    """Aplica una tool call sobre data. Devuelve un mensaje de error si es inválida, o None si se aplicó."""
    try:
        if name == "set_client":
            client_name = args.get("name")
            if not client_name:
                return "set_client requiere 'name'"
            if data.client is None:
                data.client = ClientInfo(name=client_name, contact=args.get("contact") or "")
            else:
                data.client.name = client_name
                if args.get("contact") is not None:
                    data.client.contact = args["contact"]
            return None

        if name == "add_item":
            item = Item(
                name=args["name"],
                quantity=float(args.get("quantity") or 1),
                unit_price=float(args.get("unit_price") or 0),
            )
            data.items.append(item)
            return None

        if name == "update_item":
            index = int(args["index"])
            if not (0 <= index < len(data.items)):
                return f"update_item: índice {index} fuera de rango"
            item = data.items[index]
            if args.get("name") is not None:
                item.name = args["name"]
            if args.get("quantity") is not None:
                item.quantity = float(args["quantity"])
            if args.get("unit_price") is not None:
                item.unit_price = float(args["unit_price"])
            return None

        if name == "remove_item":
            index = int(args["index"])
            if not (0 <= index < len(data.items)):
                return f"remove_item: índice {index} fuera de rango"
            data.items.pop(index)
            return None

        if name == "set_estimated_time":
            estimated_time = args.get("estimated_time")
            if not estimated_time:
                return "set_estimated_time requiere 'estimated_time'"
            data.estimated_time = estimated_time
            return None

        return f"herramienta desconocida: {name}"
    except (KeyError, TypeError, ValueError) as exc:
        return f"argumentos inválidos para {name}: {exc}"


def _state_context(data: QuoteData) -> str:
    if data.client is None and not data.items and not data.estimated_time:
        return "Estado actual: todavía no hay ningún dato cargado."

    lines = ["Estado actual de la cotización:"]
    if data.client:
        lines.append(f"- Cliente: {data.client.name} ({data.client.contact or 'sin contacto'})")
    else:
        lines.append("- Cliente: (todavía no cargado)")

    if data.items:
        lines.append("- Ítems:")
        for i, item in enumerate(data.items):
            price = item.unit_price if item.unit_price else "(sin precio)"
            lines.append(f"  [{i}] {item.quantity:g} x {item.name} — precio unitario: {price}")
    else:
        lines.append("- Ítems: (todavía no hay ninguno)")

    lines.append(f"- Tiempo estimado de realización: {data.estimated_time or '(todavía no cargado)'}")

    return "\n".join(lines)


def run_turn(data: QuoteData, text: str | None, audio: bytes | None, audio_mime: str) -> AgentResult:
    parts: list[types.Part] = [types.Part.from_text(text=_state_context(data))]
    if audio:
        parts.append(types.Part.from_bytes(data=audio, mime_type=audio_mime))
    if text:
        parts.append(types.Part.from_text(text=text))

    contents: list[types.Content] = [types.Content(role="user", parts=parts)]
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
        tools=[_TOOLS],
    )

    reply = "Se me complicó procesar eso, ¿podés reformularlo?"
    for _ in range(_MAX_TOOL_ROUNDS):
        response = _client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
        candidate = response.candidates[0]
        contents.append(candidate.content)

        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]
        if not function_calls:
            reply = response.text or ""
            break

        response_parts = []
        for call in function_calls:
            error = _apply_tool_call(data, call.name, dict(call.args or {}))
            result = {"error": error} if error else {"ok": True}
            response_parts.append(types.Part.from_function_response(name=call.name, response=result))
        contents.append(types.Content(role="tool", parts=response_parts))

    return AgentResult(data=data, reply=reply)
