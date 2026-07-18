# Bot de cotizaciones para Telegram

Bot de Telegram que arma cotizaciones (presupuestos) de productos/servicios de forma conversacional
(texto o audio, interpretado con Gemini) y devuelve un PDF descargable. Pensado para desplegarse en
Vercel (funciones serverless en modo webhook).

## Comandos

- Le contás al bot, en un solo mensaje o en varios (texto o audio), quién es el cliente, qué ítems
  (producto, cantidad, precio) querés cotizar y el tiempo estimado de realización del trabajo. No hace
  falta ningún comando para arrancar.
- El bot va completando la cotización y pregunta puntualmente por lo que falte (nombre del cliente,
  precio de algún ítem, tiempo estimado, etc.). Podés seguir agregando o corrigiendo ítems en cualquier
  momento.
- Cuando está todo completo, muestra el resumen con botones para confirmar o cancelar. Si en vez de
  tocar un botón mandás otro mensaje, se toma como una corrección y se actualiza el resumen.
- `/nueva` — descarta la cotización en curso y arranca una nueva.
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
- `BUSINESS_BANK_ACCOUNT`, `BUSINESS_ALIAS` — datos de pago que se muestran en el PDF
- `BUSINESS_SIGNATURE` — firma de despedida del PDF (ej. "Ramón y Emanuel Brunello")
- `BUSINESS_LOGO_PATH` — ruta al logo (default `src/assets/img/logo encabezado.png`)
- `BUSINESS_VALIDITY_DAYS` — días de validez del presupuesto (default `15`)
- `BUSINESS_QUOTE_PREFIX` — prefijo del número de presupuesto, ej. `002` → `N° 002-000125` (default `002`)

La sección "Otros detalles" del PDF se arma automáticamente a partir de los ítems cargados y del tiempo
estimado que indique el cliente en el chat: agrega la garantía de cámaras (Imou/Dahua, 2 años) si detecta
ítems de cámaras, la garantía de alarmas (X-28, 5 años) si detecta ítems de alarma, y siempre suma la
línea de mano de obra/accesorios incluidos y el tiempo estimado de realización.

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
business = {
    "name": "Mi Negocio",
    "phone": "+54 9 11 1234-5678",
    "email": "hola@minegocio.com",
    "address": "",
    "bank_account": "Bancor",
    "bank_alias": "MI.ALIAS.BANCARIO",
    "signature": "Juan y María",
    "logo_path": "src/assets/img/logo encabezado.png",
    "validity_days": 15,
    "quote_prefix": "002",
}
pdf_bytes = build_quote_pdf(
    business, client, items, sum(i.subtotal for i in items), quote_number=125, estimated_time="1 día",
)
open("prueba.pdf", "wb").write(pdf_bytes)
```
