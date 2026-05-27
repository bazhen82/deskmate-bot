"""
Main Bot Module.
Initializes and configures the Telegram bot using pyTelegramBotAPI.
"""

from telebot import apihelper
from telebot import asyncio_helper
from telebot.async_telebot import AsyncTeleBot

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_API_URL, USE_TELEGRAM_PROXY
from utils.logging import logger

if USE_TELEGRAM_PROXY:
    api_url = f"{TELEGRAM_API_URL}/bot{{0}}/{{1}}"
    file_url = f"{TELEGRAM_API_URL}/file/bot{{0}}/{{1}}"
    # Sync API (requests)
    apihelper.API_URL = api_url
    apihelper.FILE_URL = file_url
    # Async API (aiohttp) — используется AsyncTeleBot
    asyncio_helper.API_URL = api_url
    asyncio_helper.FILE_URL = file_url
    logger.info(f"Telegram API via Cloudflare Worker: {TELEGRAM_API_URL}")
else:
    logger.warning(
        "TELEGRAM_API_URL not set — using api.telegram.org (may not work in Russia)"
    )

# Create bot instance
bot = AsyncTeleBot(TELEGRAM_BOT_TOKEN)

logger.info("Bot instance created")
