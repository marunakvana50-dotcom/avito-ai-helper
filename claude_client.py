"""
Обёртка над нейросетью Claude (Anthropic).

Здесь всего две функции — «разобрать фото» и «улучшить описание». Вся работа с
нейросетью спрятана сюда, чтобы файл бота (bot.py) оставался простым.
"""

import base64
import os

from anthropic import AsyncAnthropic

import prompts

# Какую модель использовать. Можно поменять через переменную окружения
# ANTHROPIC_MODEL. По умолчанию — claude-opus-4-8 (качественнее).
# Более дешёвый вариант: claude-haiku-4-5.
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")

# Клиент нейросети. Ключ берётся из переменной окружения ANTHROPIC_API_KEY.
client = AsyncAnthropic()


def _extract_text(response) -> str:
    """Достаёт текстовый ответ из ответа нейросети."""
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip()


async def analyze_photo(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    """Отправляет фото в нейросеть и возвращает разбор кадра с советами."""
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompts.PHOTO_PROMPT},
                ],
            }
        ],
    )
    return _extract_text(response)


async def improve_description(text: str) -> str:
    """Отправляет описание в нейросеть и возвращает улучшенный вариант."""
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": prompts.DESCRIPTION_PROMPT + text,
            }
        ],
    )
    return _extract_text(response)
