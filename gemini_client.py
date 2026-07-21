"""
Обёртка над нейросетью Gemini (Google).

Здесь всего две функции — «разобрать фото» и «улучшить описание». Вся работа с
нейросетью спрятана сюда, чтобы файл бота (bot.py) оставался простым.
"""

import asyncio
import os

from google import genai
from google.genai import errors, types

import prompts

# Какую модель использовать. Можно поменять через переменную окружения
# GEMINI_MODEL. По умолчанию — gemini-3.5-flash (быстро, дёшево, поддерживает фото).
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# Необязательно: прокси именно для запросов к Gemini (например, если в твоей
# стране Gemini API недоступен напрямую). Не влияет на остальной код бота —
# Telegram по-прежнему работает через обычное сетевое подключение.
# Формат: socks5://логин:пароль@хост:порт  или  http://логин:пароль@хост:порт
_proxy_url = os.environ.get("GEMINI_PROXY_URL")
_http_options = types.HttpOptions(
    client_args={"proxy": _proxy_url},
    async_client_args={"proxy": _proxy_url},
) if _proxy_url else None

# Клиент нейросети. Ключ берётся из переменной окружения GEMINI_API_KEY.
client = genai.Client(http_options=_http_options)

# Если Gemini временно перегружен (ошибка 503) — сколько раз повторить попытку
# и сколько секунд ждать между попытками, прежде чем сдаться.
_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 3


async def _generate_with_retry(contents) -> str:
    """Отправляет запрос к нейросети; при перегрузке (503) повторяет попытку."""
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(max_output_tokens=3000),
            )
            return (response.text or "").strip()
        except errors.ServerError as error:
            last_error = error
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAY_SECONDS)
    raise last_error


async def analyze_photo(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    """Отправляет фото в нейросеть и возвращает разбор кадра с советами."""
    return await _generate_with_retry([
        types.Part.from_bytes(data=image_bytes, mime_type=media_type),
        prompts.PHOTO_PROMPT,
    ])


async def improve_description(text: str) -> str:
    """Отправляет описание в нейросеть и возвращает улучшенный вариант."""
    return await _generate_with_retry(prompts.DESCRIPTION_PROMPT + text)
