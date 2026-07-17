# Bot de cotizaciones para Telegram

Bot de Telegram que arma cotizaciones (presupuestos) de productos/servicios de forma conversacional
(texto o audio, interpretado con Gemini) y devuelve un PDF descargable. Pensado para desplegarse en
Vercel (funciones serverless en modo webhook).

## Comandos

- `/nueva` — empieza una cotización nueva.
- Contás el cliente (texto o audio).
- Vas contando los ítems (producto, cantidad, precio), de a uno o todos juntos.
- `/listo` — cierra la carga de ítems y muestra el resumen con botones para confirmar o cancelar.
- `/cancelar` — cancela la cotización en curso.
- `/historial` — muestra las últimas cotizaciones y permite volver a descargar el PDF de cualquiera.

## Setup

### 1. Crear el bot en Telegram

Hablá con [@BotFather](https://t.me/BotFather), `/newbot`, y guardá el token (`TELEGRAM_BOT_TOKEN`).

### 2. Conseguir una API key de Gemini

Creála en [Google AI Studio](https://aistudio.google.com/apikey) (`GEMINI_API_KEY`).

### 3. Crear el proyecto en Supabase

1. Creá un proyecto en [supabase.com](https://supabase.com).
2. Andá al SQL Editor y corré el contenido de `migrations/001_init.sql`.
3. Copiá la URL del proyecto (`SUPABASE_URL`) y una API key (Settings → API; `SUPABASE_KEY`, service_role
   si vas a insertar/leer sin políticas RLS, o configurá RLS si preferís usar la anon key).

### 4. Variables de entorno

Copiá `.env.example` a `.env` (para referencia local) y cargá las mismas variables en Vercel:
Project → Settings → Environment Variables.

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET` (elegí cualquier string; se usa para validar que el webhook viene de Telegram)
- `GEMINI_API_KEY`
- `SUPABASE_URL`, `SUPABASE_KEY`
- `BUSINESS_NAME`, `BUSINESS_PHONE`, `BUSINESS_EMAIL`, `BUSINESS_ADDRESS`

### 5. Deploy

```bash
npm install -g vercel   # si no lo tenés
vercel deploy --prod
```

### 6. Registrar el webhook

Una vez desplegado, apuntá el bot a la URL pública:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -d "url=https://<tu-deploy>.vercel.app/api/webhook" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

Listo — escribile `/nueva` al bot en Telegram para probarlo.

## Desarrollo local

```bash
pip install -r requirements.txt
```

Para probar la generación de PDF sin depender de Telegram/Gemini/Supabase:

```python
from bot.models import ClientInfo, Item
from bot.pdf import build_quote_pdf

client = ClientInfo(name="Juan Pérez", contact="juan@mail.com")
items = [Item(name="Silla", quantity=3, unit_price=50), Item(name="Mesa", quantity=1, unit_price=200)]
pdf_bytes = build_quote_pdf(
    {"name": "Mi Negocio", "phone": "+54 9 11 1234-5678", "email": "hola@minegocio.com", "address": ""},
    client, items, sum(i.subtotal for i in items),
)
open("prueba.pdf", "wb").write(pdf_bytes)
```
