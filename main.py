"""
Main Entry Point.
Starts the Telegram bot using pyTelegramBotAPI.
"""

import asyncio
import sys

from telebot import types
from bot import bot
from utils.logging import logger
from utils.instance_lock import acquire_instance_lock, release_instance_lock
from utils.telegram_files import get_updates_post, TelegramApiError


async def clear_pending_updates() -> None:
    """Acknowledge all pending updates without running handlers."""
    total = 0
    offset = bot.offset if bot.offset is not None else 0

    for attempt in range(3):
        try:
            batch_total = 0
            for _ in range(100):
                updates_raw = await get_updates_post(
                    offset=offset, limit=100, timeout=0
                )
                if not updates_raw:
                    break
                offset = updates_raw[-1]["update_id"] + 1
                bot.offset = offset
                batch_total += len(updates_raw)

            tail = await get_updates_post(offset=offset, limit=100, timeout=0)
            if tail:
                offset = tail[-1]["update_id"] + 1
                bot.offset = offset
                batch_total += len(tail)

            total += batch_total
            logger.info(
                f"Cleared {total} pending updates"
                + (f" (offset={bot.offset})" if bot.offset is not None else "")
            )
            return
        except Exception as e:
            if attempt < 2:
                logger.warning(f"Queue clear retry {attempt + 1}/3: {e}")
                await asyncio.sleep(2)
            else:
                logger.warning(f"Could not clear pending updates: {e}")


async def run_polling() -> None:
    """Short polling loop via POST getUpdates (Worker-safe)."""
    from utils.bot_state import mark_polling_ready, should_process_update

    mark_polling_ready()
    handler_sem = asyncio.Semaphore(1)

    async def dispatch_update(update):
        if not should_process_update(update):
            return
        async with handler_sem:
            try:
                await bot.process_new_updates([update])
            except Exception as e:
                logger.error(f"Handler error: {e}", exc_info=True)

    while True:
        try:
            updates_raw = await get_updates_post(
                offset=bot.offset,
                limit=10,
                timeout=0,
            )
            if updates_raw:
                updates = [types.Update.de_json(u) for u in updates_raw]
                bot.offset = updates[-1].update_id + 1
                for update in updates:
                    asyncio.create_task(dispatch_update(update))
            await asyncio.sleep(1)
        except KeyboardInterrupt:
            raise
        except TelegramApiError as e:
            logger.warning(f"getUpdates error, retrying: {e}")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Polling error: {e}", exc_info=True)
            await asyncio.sleep(3)


async def setup_bot():
    """Setup bot with handlers and initialize RAG if needed."""
    logger.info("Bot starting up...")
    
    # Import handlers (they will register themselves via decorators)
    try:
        from handlers import start, text, voice, image, document_upload
        logger.info("Handlers imported successfully")
    except Exception as e:
        logger.error(f"Error importing handlers: {e}", exc_info=True)
        raise
    
    # Initialize RAG index only if empty (avoid blocking startup every time)
    try:
        from rag.index import vector_index
        from config import DOCUMENTS_DIR
        
        stats = vector_index.get_stats()
        indexed_count = stats.get("total_documents", 0)

        docs = list(DOCUMENTS_DIR.glob('*'))
        docs = [d for d in docs if d.is_file() and d.suffix in ['.pdf', '.txt', '.md']]

        if indexed_count > 0:
            logger.info(f"RAG index ready: {indexed_count} chunks")
        elif docs:
            logger.info(f"Found {len(docs)} documents, indexing (first run)...")
            loop = asyncio.get_running_loop()
            count = await loop.run_in_executor(
                None,
                lambda: vector_index.index_documents_directory(force_reindex=False),
            )
            logger.info(f"Indexed {count} document chunks")
        else:
            logger.info("No documents found in data/documents/")
    
    except Exception as e:
        logger.warning(f"Could not initialize RAG index: {e}")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Could not get bot info: {e}")


async def shutdown_bot():
    """Actions to perform on bot shutdown."""
    logger.info("Bot shutting down...")
    try:
        await bot.close_session()
    except:
        pass
    release_instance_lock()
    logger.info("Bot shutdown complete")


async def main():
    """Main function to run the bot."""
    try:
        await setup_bot()

        await bot.delete_webhook(drop_pending_updates=True)
        await clear_pending_updates()
        
        # Short polling works reliably through Cloudflare Worker (long poll hangs)
        logger.info("Bot is ready. Send /start in Telegram.")
        await run_polling()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await shutdown_bot()


if __name__ == "__main__":
    try:
        acquire_instance_lock()
        logger.info("="*60)
        logger.info("Personal Assistant Bot - Starting")
        logger.info("="*60)
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)
    finally:
        release_instance_lock()
