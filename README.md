# DeskMate — мультимодальный Telegram-ассистент

Ops-ассистент для студии [NeiroBridge](https://neirobridge.ru): текст, голос, RAG, Vision и генерация изображений.

## Возможности

- **Текст** — диалог с GPT-4o, история сообщений
- **RAG** — ответы из базы знаний (ChromaDB) с указанием источника
- **Голос** — Whisper (STT) + TTS (режим `/mode voice`)
- **Vision** — анализ фото и скриншотов (GPT-4o Vision)
- **Генерация изображений** — gpt-image-1 через ProxyAPI (команда `/image` или «Нарисуй…»)

## Стек

- Python 3.10+, pyTelegramBotAPI
- OpenAI через [ProxyAPI](https://proxyapi.ru) (GPT-4o, Whisper, TTS, Vision, gpt-image-1)
- LangChain + ChromaDB (RAG)
- Cloudflare Worker — прокси Telegram Bot API для РФ

## Быстрый старт

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # заполнить ключи
python main.py
```

Или `run.bat` на Windows.

### Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_URL` | URL Cloudflare Worker (без `/bot...`) |
| `OPENAI_API_KEY` | Ключ ProxyAPI |
| `USE_PROXYAPI` | `true` (по умолчанию) |
| `IMAGE_GEN_MODEL` | `gpt-image-1` (по умолчанию) |

### Cloudflare Worker

Код прокси: [`cloudflare/telegram-proxy.js`](cloudflare/telegram-proxy.js).  
Разверните в Cloudflare Workers и укажите URL в `TELEGRAM_API_URL`.

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/mode text\|voice\|rag` | Режим работы |
| `/stats` | Статус базы знаний RAG |
| `/image <описание>` | Генерация изображения |
| `/reset` | Сброс истории диалога |

## Структура проекта

```
handlers/     — команды и входящие сообщения
services/     — OpenAI, router, STT/TTS, Vision, image generation
rag/          — индексация и поиск в ChromaDB
utils/        — логи, сессии, Telegram API helpers
data/documents/ — файлы базы знаний (txt)
cloudflare/   — Worker для Telegram API
```

## Пайплайн

```
Пользователь (Telegram) -> Cloudflare Worker -> handlers/ -> router.py
  -> ProxyAPI (GPT-4o / Whisper / TTS / Vision / gpt-image-1) + ChromaDB (RAG)
  -> ответ в Telegram
```

## База знаний RAG

Файлы в `data/documents/` индексируются при старте. Пример: `product_guide.txt`, `pricing_and_offers.txt`, `integrations_workflows.txt`.

Режим: `/mode rag`

## Ограничения (РФ + Telegram)

Прямой доступ к `api.telegram.org` из России ограничен. Проект использует Cloudflare Worker как reverse proxy. Текст, RAG и Vision работают стабильно; загрузка медиа (`sendVoice`, `sendPhoto`) через прокси может падать по таймауту — это инфраструктурное ограничение, не ошибка бизнес-логики.

## Лицензия

MIT
