"""
Document Upload Handler (Optional).
Allows users to upload documents directly through the bot using pyTelegramBotAPI.
"""

from telebot import types
from pathlib import Path

from bot import bot
from config import DOCUMENTS_DIR
from rag.loader import document_loader
from rag.index import vector_index
from utils.logging import logger
from utils.telegram_files import download_telegram_file


# This handler is included but currently the main document handler 
# in image.py provides basic functionality. This can be enhanced later.

async def process_document_upload(message: types.Message, document: types.Document):
    """Process document upload for RAG."""
    user_id = message.from_user.id
    
    # Check file type
    supported_types = [
        'application/pdf',
        'text/plain',
        'text/markdown'
    ]
    
    if document.mime_type not in supported_types:
        await bot.send_message(
            message.chat.id,
            f"❌ Неподдерживаемый тип файла: {document.mime_type}\n\n"
            "Поддерживаемые форматы:\n"
            "• PDF (.pdf)\n"
            "• Text (.txt)\n"
            "• Markdown (.md)"
        )
        return
    
    # Check file size (max 20 MB)
    max_size = 20 * 1024 * 1024  # 20 MB
    if document.file_size > max_size:
        await bot.send_message(
            message.chat.id,
            f"❌ Файл слишком большой: {document.file_size / 1024 / 1024:.1f} MB\n"
            f"Максимальный размер: 20 MB"
        )
        return
    
    try:
        await bot.send_message(message.chat.id, "⏳ Загружаю документ...")
        
        # Download file (POST getFile — required for Worker proxy)
        file_bytes = await download_telegram_file(document.file_id)
        file_path = DOCUMENTS_DIR / document.file_name
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        logger.info(f"User {user_id} uploaded document: {document.file_name}")
        
        # Index document
        await bot.send_message(message.chat.id, "📄 Индексирую документ...")
        
        # Load and chunk document
        chunks = document_loader.load_document(file_path)
        
        # Add to vector store
        vector_index.add_documents(chunks)
        
        logger.info(f"Indexed {len(chunks)} chunks from {document.file_name}")
        
        # Success message
        await bot.send_message(
            message.chat.id,
            f"✅ Документ успешно загружен!\n\n"
            f"📄 Файл: {document.file_name}\n"
            f"📊 Фрагментов: {len(chunks)}\n"
            f"💾 Размер: {document.file_size / 1024:.1f} KB\n\n"
            f"Теперь вы можете задавать вопросы по этому документу:\n"
            f"/mode rag"
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        await bot.send_message(
            message.chat.id,
            f"❌ Ошибка при загрузке документа:\n{str(e)}\n\n"
            "Попробуйте загрузить файл вручную в папку data/documents/"
        )
