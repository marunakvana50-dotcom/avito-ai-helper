"""
Вебхук-эндпоинт для деплоя на Vercel.

В отличие от локального запуска (bot.py -> run_polling, бот сам опрашивает
Telegram), здесь всё наоборот: Telegram сам присылает сюда HTTP POST-запрос
при каждом новом сообщении. Vercel запускает этот файл как serverless-функцию
по адресу /api/webhook.

Как включить: смотри README.md, раздел "Деплой на Vercel".
"""

import asyncio
import json
import logging
import os
from http.server import BaseHTTPRequestHandler

from dotenv import load_dotenv

load_dotenv()

from telegram import Update

from bot import build_application

logger = logging.getLogger(__name__)

# Необязательно: секретный токен, которым Telegram подписывает каждый запрос
# к вебхуку (заголовок X-Telegram-Bot-Api-Secret-Token). Задаётся при
# регистрации вебхука (см. set_webhook.py) и здесь же проверяется — так
# посторонний не сможет слать боту поддельные апдейты.
_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")


async def _process_update(update_data: dict) -> None:
    """Разбирает один апдейт от Telegram и прогоняет его через обработчики бота."""
    application = build_application()
    async with application:
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 (имя метода задаёт сам Vercel)
        if _WEBHOOK_SECRET and self.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        ) != _WEBHOOK_SECRET:
            self.send_response(401)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"

        try:
            update_data = json.loads(body or b"{}")
            asyncio.run(_process_update(update_data))
        except Exception:
            logger.exception("Ошибка при обработке апдейта из вебхука")

        # Telegram нужен ответ 200, иначе он будет повторно слать тот же апдейт.
        self.send_response(200)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        """Простая проверка живости — открыть URL вебхука в браузере."""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
