"""
Telegram-бот с ИИ-ассистентом (OpenAI GPT) и обработкой фотографий.

Возможности:
- /start, /help — приветствие и помощь
- Текстовые сообщения — ответ через OpenAI (Chat Completions API)
- Фотографии — анализ изображения через GPT vision (gpt-4o и т.п.)
- Хранение короткой истории диалога в памяти (на пользователя)

Запуск:
    python bot.py

Перед запуском заполните .env (см. .env.example)
"""

import base64
import logging
import os
from collections import defaultdict, deque

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Настройка
# ---------------------------------------------------------------------------

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты — дружелюбный ИИ-ассистент в Telegram. Отвечай кратко, "
    "по делу и на языке пользователя.",
)

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN в переменных окружения (.env)")
if not OPENAI_API_KEY:
    raise RuntimeError("Не задан OPENAI_API_KEY в переменных окружения (.env)")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

# История диалога по каждому пользователю: user_id -> deque[{"role","content"}]
user_histories: dict[int, deque] = defaultdict(
    lambda: deque(maxlen=MAX_HISTORY_MESSAGES)
)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def ask_openai(user_id: int, user_text: str) -> str:
    """Отправляет текстовое сообщение в OpenAI с учётом истории диалога."""
    history = user_histories[user_id]
    history.append({"role": "user", "content": user_text})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=1024,
        messages=messages,
    )

    reply_text = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply_text})
    return reply_text


def ask_openai_about_image(image_bytes: bytes, caption: str | None) -> str:
    """Отправляет изображение в OpenAI vision и возвращает описание/ответ."""
    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")
    prompt_text = caption or "Опиши, что изображено на этом фото, подробно и по-русски."

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        },
                    },
                ],
            },
        ],
    )

    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Хендлеры команд
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я ИИ-ассистент на базе OpenAI.\n\n"
        "— Напиши мне вопрос текстом, и я отвечу.\n"
        "— Пришли фото (можно с подписью-вопросом), и я его проанализирую.\n\n"
        "Команды:\n"
        "/start — это сообщение\n"
        "/help — помощь\n"
        "/reset — очистить историю диалога"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Просто пиши мне сообщения или присылай фотографии.\n"
        "Если хочешь задать вопрос о фото — добавь подпись к изображению.\n"
        "/reset — начать диалог заново (очистить память)."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_histories.pop(update.effective_user.id, None)
    await update.message.reply_text("История диалога очищена.")


# ---------------------------------------------------------------------------
# Хендлеры сообщений
# ---------------------------------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_text = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    try:
        reply = ask_openai(user_id, user_text)
    except Exception:
        logger.exception("Ошибка при обращении к OpenAI API (текст)")
        reply = "Извините, произошла ошибка при обработке запроса. Попробуйте позже."

    await update.message.reply_text(reply)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    # Берём фото в наилучшем доступном качестве
    photo = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo.file_id)
    photo_bytes = bytes(await tg_file.download_as_bytearray())

    caption = update.message.caption

    try:
        reply = ask_openai_about_image(photo_bytes, caption)
    except Exception:
        logger.exception("Ошибка при обращении к OpenAI API (фото)")
        reply = "Извините, не удалось обработать изображение. Попробуйте позже."

    await update.message.reply_text(reply)


async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Я умею обрабатывать текстовые сообщения и фотографии. "
        "Другие типы файлов пока не поддерживаются."
    )


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    application.add_handler(
        MessageHandler(~filters.TEXT & ~filters.PHOTO & ~filters.COMMAND, handle_unsupported)
    )

    logger.info("Бот запущен. Ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
