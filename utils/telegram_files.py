"""Telegram file/API helpers with explicit timeouts (Worker-safe)."""

import asyncio
import json
import shutil
import subprocess
import urllib.request
from typing import Optional

import aiohttp

from config import (
    TELEGRAM_API_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_DIRECT_FILES,
    USE_TELEGRAM_PROXY,
)
from utils.logging import logger

API_BASE = TELEGRAM_API_URL if USE_TELEGRAM_PROXY else "https://api.telegram.org"
API_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=25)
DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=50, connect=10, sock_read=40)
DIRECT_FILE_BASE = "https://api.telegram.org"
SYNC_READ_TIMEOUT = 45


class TelegramApiError(RuntimeError):
    pass


async def _api_post(method: str, params: dict) -> dict:
    url = f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/{method}"
    async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
        async with session.post(url, data=params) as resp:
            text = await resp.text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                raise TelegramApiError(
                    f"{method}: invalid JSON (status {resp.status}): {text[:120]}"
                ) from e
            if not data.get("ok"):
                raise TelegramApiError(data.get("description", f"{method} failed"))
            return data["result"]


async def get_updates_post(
    offset: Optional[int] = None,
    limit: int = 100,
    timeout: int = 0,
) -> list:
    """getUpdates via POST — GET breaks through Cloudflare Worker."""
    params: dict[str, str] = {
        "limit": str(limit),
        "timeout": str(timeout),
    }
    if offset is not None:
        params["offset"] = str(offset)

    url = f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
        async with session.post(url, data=params) as resp:
            text = await resp.text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                raise TelegramApiError(
                    f"getUpdates: invalid JSON (status {resp.status}): {text[:120]}"
                ) from e
            if not data.get("ok"):
                raise TelegramApiError(
                    data.get("description", "getUpdates failed")
                )
            return data.get("result") or []


async def get_file_info(file_id: str) -> dict:
    return await _api_post("getFile", {"file_id": file_id})


def _download_urls(file_path: str) -> list[str]:
    urls = [f"{API_BASE}/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"]
    if USE_TELEGRAM_PROXY and TELEGRAM_DIRECT_FILES:
        direct = f"{DIRECT_FILE_BASE}/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        if direct not in urls:
            urls.append(direct)
    elif not USE_TELEGRAM_PROXY:
        pass
    return urls


def _download_url_sync(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "DeskMateBot/1.0"})
    with urllib.request.urlopen(req, timeout=SYNC_READ_TIMEOUT) as resp:
        return resp.read()


def _download_url_curl(url: str) -> bytes:
    if not shutil.which("curl"):
        raise TelegramApiError("curl not found")
    result = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", str(SYNC_READ_TIMEOUT), url],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace")[:200]
        raise TelegramApiError(f"curl failed ({result.returncode}): {err}")
    if not result.stdout:
        raise TelegramApiError("curl returned empty body")
    return result.stdout


async def _download_url_aiohttp(url: str) -> bytes:
    async with aiohttp.ClientSession(timeout=DOWNLOAD_TIMEOUT) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise TelegramApiError(
                    f"HTTP {resp.status}: {body[:120]}"
                )
            chunks = []
            async for chunk in resp.content.iter_chunked(16384):
                chunks.append(chunk)
            data = b"".join(chunks)
            if not data:
                raise TelegramApiError("empty file body")
            return data


async def download_telegram_file(file_id: str) -> bytes:
    info = await get_file_info(file_id)
    file_path = info["file_path"]
    logger.info(f"Downloading Telegram file: {file_path}")

    loop = asyncio.get_running_loop()
    last_error = None

    # Proxy URL only by default (direct needs VPN — set TELEGRAM_DIRECT_FILES=true)
    for round_num in range(3):
        for url in _download_urls(file_path):
            label = "proxy" if url.startswith(API_BASE) else "direct"

            for fn, name in (
                (_download_url_curl, "curl"),
                (_download_url_sync, "urllib"),
            ):
                try:
                    logger.info(f"Download {label}/{name} (round {round_num + 1})")
                    data = await loop.run_in_executor(None, fn, url)
                    logger.info(f"Downloaded {len(data)} bytes via {label}/{name}")
                    return data
                except Exception as e:
                    last_error = e
                    logger.warning(f"{label}/{name} failed: {e}")

            try:
                logger.info(f"Download {label}/aiohttp (round {round_num + 1})")
                data = await _download_url_aiohttp(url)
                logger.info(f"Downloaded {len(data)} bytes via {label}/aiohttp")
                return data
            except Exception as e:
                last_error = e
                logger.warning(f"{label}/aiohttp failed: {e}")

        if round_num < 2:
            await asyncio.sleep(2)

    hint = (
        " Проверьте Worker (cloudflare/telegram-proxy.js → Deploy) "
        "или включите VPN и TELEGRAM_DIRECT_FILES=true в .env."
    )
    raise TelegramApiError(f"All download methods failed: {last_error}.{hint}")


def build_file_url(file_path: str) -> str:
    return f"{API_BASE}/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"


async def send_message_safe(chat_id: int, text: str, retries: int = 3) -> None:
    """Send message with retry on 429/timeout."""
    from bot import bot

    last_error = None
    for attempt in range(retries):
        try:
            await bot.send_message(chat_id, text)
            return
        except Exception as e:
            last_error = e
            err = str(e).lower()
            wait = 3
            if "retry after" in err:
                for part in str(e).split():
                    if part.isdigit():
                        wait = int(part)
                        break
            logger.warning(f"sendMessage retry {attempt + 1}/{retries}: {e}")
            await asyncio.sleep(min(wait, 30))
    raise last_error


UPLOAD_TIMEOUT = aiohttp.ClientTimeout(total=120, connect=15, sock_read=90)


async def send_voice_safe(chat_id: int, audio_path: str, retries: int = 3) -> None:
    """Upload voice file via direct aiohttp POST (more reliable through Worker)."""
    from pathlib import Path

    path = Path(audio_path)
    url = f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    audio_bytes = path.read_bytes()

    last_error = None
    for attempt in range(retries):
        try:
            form = aiohttp.FormData()
            form.add_field("chat_id", str(chat_id))
            form.add_field(
                "voice",
                audio_bytes,
                filename="voice.mp3",
                content_type="audio/mpeg",
            )
            async with aiohttp.ClientSession(timeout=UPLOAD_TIMEOUT) as session:
                async with session.post(url, data=form) as resp:
                    text = await resp.text()
                    data = json.loads(text)
                    if not data.get("ok"):
                        raise TelegramApiError(
                            data.get("description", "sendVoice failed")
                        )
            logger.info(f"Voice sent to chat {chat_id}")
            return
        except Exception as e:
            last_error = e
            logger.warning(f"sendVoice retry {attempt + 1}/{retries}: {e}")
            await asyncio.sleep(min(3 * (attempt + 1), 15))
    raise last_error


async def send_photo_safe(
    chat_id: int,
    photo_path: str,
    caption: Optional[str] = None,
    retries: int = 3,
) -> None:
    """Upload photo via direct aiohttp POST (more reliable through Worker)."""
    from pathlib import Path

    path = Path(photo_path)
    url = f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    photo_bytes = path.read_bytes()
    content_type = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"

    last_error = None
    for attempt in range(retries):
        try:
            form = aiohttp.FormData()
            form.add_field("chat_id", str(chat_id))
            if caption:
                form.add_field("caption", caption[:1024])
            form.add_field(
                "photo",
                photo_bytes,
                filename=path.name,
                content_type=content_type,
            )
            async with aiohttp.ClientSession(timeout=UPLOAD_TIMEOUT) as session:
                async with session.post(url, data=form) as resp:
                    text = await resp.text()
                    data = json.loads(text)
                    if not data.get("ok"):
                        raise TelegramApiError(
                            data.get("description", "sendPhoto failed")
                        )
            logger.info(f"Photo sent to chat {chat_id} ({len(photo_bytes) // 1024} KB)")
            return
        except Exception as e:
            last_error = e
            logger.warning(f"sendPhoto retry {attempt + 1}/{retries}: {e}")
            await asyncio.sleep(min(3 * (attempt + 1), 15))
    raise last_error
