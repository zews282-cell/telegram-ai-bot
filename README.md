# Telegram AI Bot (Claude)

Telegram-бот с ИИ-ассистентом на базе Claude (Anthropic API) и поддержкой обработки фотографий.

## Возможности

- 💬 Отвечает на текстовые сообщения через Claude
- 🖼️ Анализирует присланные фотографии (в том числе с вопросом-подписью)
- 🧠 Хранит короткую историю диалога для каждого пользователя
- ♻️ Команда `/reset` для очистки истории

## Установка

1. Склонируйте репозиторий:
   ```bash
   git clone <ваш-репозиторий>
   cd telegram-ai-bot
   ```

2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Скопируйте `.env.example` в `.env` и заполните переменные:
   ```bash
   cp .env.example .env
   ```
   - `TELEGRAM_BOT_TOKEN` — получить у [@BotFather](https://t.me/BotFather)
   - `ANTHROPIC_API_KEY` — получить в [консоли Anthropic](https://console.anthropic.com/)

4. Запустите бота:
   ```bash
   python bot.py
   ```

## Структура проекта

```
telegram-ai-bot/
├── bot.py              # основная логика бота
├── requirements.txt    # зависимости
├── .env.example        # пример переменных окружения
├── .gitignore
└── README.md
```

## Развёртывание

Бот использует long polling, поэтому его можно запускать на любом сервере/VPS
(например, через `systemd`, `screen`/`tmux`, Docker или PaaS вроде Railway/Render).

Пример простого systemd-сервиса:

```ini
[Unit]
Description=Telegram AI Bot
After=network.target

[Service]
WorkingDirectory=/opt/telegram-ai-bot
ExecStart=/opt/telegram-ai-bot/venv/bin/python bot.py
Restart=always
EnvironmentFile=/opt/telegram-ai-bot/.env

[Install]
WantedBy=multi-user.target
```

## Настройка модели

Модель Claude задаётся переменной `CLAUDE_MODEL` в `.env` (по умолчанию `claude-sonnet-4-6`).
Системный промпт (характер ассистента) можно изменить через `SYSTEM_PROMPT`.

## Лицензия

MIT
