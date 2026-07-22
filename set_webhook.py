"""
Утилита: включить или выключить вебхук Telegram-бота после деплоя на Vercel.

Использование:
    python3 set_webhook.py https://твой-проект.vercel.app
        -> включает вебхук (Telegram начнёт слать апдейты на Vercel)

    python3 set_webhook.py --delete
        -> выключает вебхук (можно вернуться к локальному запуску `python bot.py`)

    python3 set_webhook.py --info
        -> показывает текущие настройки вебхука у бота

Токен берётся из .env (TELEGRAM_BOT_TOKEN). Если задан TELEGRAM_WEBHOOK_SECRET
в .env — он же передаётся Telegram, чтобы вебхук проверял подлинность запросов.
"""

import os
import sys
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()


def _call(method: str, params: dict | None = None) -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Не задан TELEGRAM_BOT_TOKEN (смотри .env)")

    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        url += f"?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as response:
        return response.read().decode()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)

    arg = sys.argv[1]

    if arg == "--delete":
        print(_call("deleteWebhook"))
        return

    if arg == "--info":
        print(_call("getWebhookInfo"))
        return

    base_url = arg.rstrip("/")
    params = {"url": f"{base_url}/api/webhook"}

    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if secret:
        params["secret_token"] = secret

    print(_call("setWebhook", params))


if __name__ == "__main__":
    main()
