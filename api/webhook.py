import json
from http.server import BaseHTTPRequestHandler

from bot import handlers
from bot.config import TELEGRAM_WEBHOOK_SECRET


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if TELEGRAM_WEBHOOK_SECRET:
            secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret != TELEGRAM_WEBHOOK_SECRET:
                self.send_response(401)
                self.end_headers()
                return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        update = json.loads(body or b"{}")

        try:
            if "message" in update:
                handlers.handle_message(update["message"])
            elif "callback_query" in update:
                handlers.handle_callback_query(update["callback_query"])
        except Exception:
            # No relanzamos: Telegram reintenta el webhook si respondemos con error,
            # y preferimos loguear (stdout, visible en los logs de Vercel) y devolver 200.
            import traceback

            traceback.print_exc()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
