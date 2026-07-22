"""
ИИ-помощник продавца на Авито — Telegram-бот (первая версия).

Что умеет:
  1. Продавец присылает фото товара -> бот разбирает кадр и советует, как переснять.
  2. Продавец присылает текст описания -> бот переписывает его в продающее.

Как запустить — смотри README.md.
"""

import logging
import os

from dotenv import load_dotenv

# Загружаем секреты из файла .env (токен бота, ключ нейросети) до всего остального.
load_dotenv()

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import gemini_client

# Простой лог в консоль — чтобы видеть, что бот работает и что идёт не так.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Telegram не даёт отправить сообщение длиннее 4096 символов.
TELEGRAM_MAX_LEN = 4000


async def _reply_long(update: Update, text: str) -> None:
    """Отправляет ответ, при необходимости разбивая длинный текст на части."""
    if not text:
        text = "Не удалось получить ответ от нейросети. Попробуй ещё раз."
    for i in range(0, len(text), TELEGRAM_MAX_LEN):
        await update.message.reply_text(text[i : i + TELEGRAM_MAX_LEN])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие и короткая инструкция."""
    await update.message.reply_text(
        "Привет! Я — ИИ-помощник продавца на Авито.\n\n"
        "Что я умею:\n"
        "📷 Пришли фото товара — разберу кадр и подскажу, как переснять, "
        "чтобы товар смотрелся лучше.\n"
        "✍️ Пришли текст описания — перепишу его в продающее объявление.\n\n"
        "Просто скинь мне фото или текст."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Продавец прислал фото — разбираем кадр."""
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        # Берём самую большую версию фото и скачиваем её.
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        image_bytes = bytes(await tg_file.download_as_bytearray())

        advice = await gemini_client.analyze_photo(image_bytes)
        await _reply_long(update, advice)
    except Exception:
        logger.exception("Ошибка при разборе фото")
        await update.message.reply_text(
            "Не получилось разобрать фото. Попробуй прислать его ещё раз."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Продавец прислал текст — улучшаем описание."""
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        improved = await gemini_client.improve_description(update.message.text)
        await _reply_long(update, improved)
    except Exception:
        logger.exception("Ошибка при улучшении описания")
        await update.message.reply_text(
            "Не получилось обработать описание. Попробуй ещё раз."
        )


def build_application() -> Application:
    """Собирает бота и регистрирует обработчики (без запуска).

    Используется и для локального запуска через long polling (main, ниже),
    и для вебхука на Vercel (api/webhook.py) — там polling не нужен, Telegram
    сам присылает апдейты HTTP-запросом.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Не задан токен бота. Установи переменную окружения TELEGRAM_BOT_TOKEN "
            "(смотри README.md)."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return app


def main() -> None:
    """Точка входа для локального запуска (long polling)."""
    app = build_application()
    logger.info("Бот запущен. Нажми Ctrl+C, чтобы остановить.")
    app.run_polling()


if __name__ == "__main__":
    main()
