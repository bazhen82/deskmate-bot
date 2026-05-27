"""
Image Handler.
Handles image analysis with GPT-4 Vision using pyTelegramBotAPI.
"""

from telebot import types
from bot import bot
from services.router import route_image_request
from utils.logging import logger
from utils.helpers import cleanup_file, safe_chat_action, save_file_async
from utils.telegram_files import download_telegram_file


@bot.message_handler(content_types=['photo'])
async def handle_photo_message(message: types.Message):
    """Handle photo messages."""
    user_id = message.from_user.id
    
    logger.info(f"Photo message from user {user_id}")
    
    # Show typing indicator
    await safe_chat_action(bot, message.chat.id, 'typing')
    
    image_path = None
    
    try:
        # Get the largest photo
        photo = message.photo[-1]
        
        # Get caption if provided
        caption = message.caption
        
        # Download photo locally (POST getFile — required for Worker proxy)
        photo_bytes = await download_telegram_file(photo.file_id)
        image_path = await save_file_async(photo_bytes, "jpg")
        
        logger.debug(f"Image saved: {image_path}")
        
        # Notify user
        if caption:
            await bot.send_message(
                message.chat.id,
                f"📸 Анализирую изображение с вопросом:\n_{caption}_"
            )
        else:
            await bot.send_message(message.chat.id, "📸 Анализирую изображение...")
        
        # Process image request (base64 — no direct Telegram URL needed)
        response = await route_image_request(
            user_id=user_id,
            image_path=image_path,
            caption=caption
        )
        
        # Send analysis result
        await bot.send_message(
            message.chat.id,
            f"🔍 **Анализ изображения:**\n\n{response['text']}"
        )
    
    except Exception as e:
        logger.error(f"Error handling photo message: {e}", exc_info=True)
        await bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при анализе изображения.\n"
            "Попробуйте отправить другое изображение."
        )
    finally:
        if image_path:
            cleanup_file(image_path)


@bot.message_handler(content_types=['document'])
async def handle_document_message(message: types.Message):
    """Handle document messages (could be PDFs for RAG)."""
    user_id = message.from_user.id
    document = message.document
    
    # Check if it's a supported document type
    if document.mime_type == "application/pdf":
        await bot.send_message(
            message.chat.id,
            "📄 PDF документ получен!\n\n"
            "Для добавления документов в базу знаний:\n"
            "1. Скачайте документ\n"
            "2. Поместите его в папку `data/documents/`\n"
            "3. Перезапустите бота или используйте команду индексации\n"
            "4. Переключитесь в режим RAG: /mode rag\n\n"
            "⚠️ Автоматическая загрузка документов будет добавлена в следующей версии."
        )
    elif document.mime_type and document.mime_type.startswith("image/"):
        # Handle as image
        await bot.send_message(
            message.chat.id,
            "📸 Получено изображение в виде документа.\n"
            "Отправьте изображение как фото для анализа."
        )
    else:
        await bot.send_message(
            message.chat.id,
            f"ℹ️ Получен файл: {document.file_name}\n"
            f"Тип: {document.mime_type}\n\n"
            "Поддерживаемые типы для анализа:\n"
            "• Изображения (отправляйте как фото)\n"
            "• PDF документы (для базы знаний)"
        )
