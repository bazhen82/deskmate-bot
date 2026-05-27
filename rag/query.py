"""
RAG Query Handler.
Handles queries against the knowledge base with context-aware responses.
"""

from typing import List, Dict, Optional
import asyncio

from rag.index import vector_index
from services.openai_client import openai_client
from utils.logging import logger
from config import RAG_TOP_K


async def query_knowledge_base(
    query: str,
    conversation_history: Optional[List[Dict]] = None
) -> str:
    """
    Query the knowledge base and generate response.
    
    Args:
        query: User's query
        conversation_history: Previous conversation messages
    
    Returns:
        Generated response based on retrieved context
    """
    try:
        # Search for relevant documents (blocking — run in thread pool)
        logger.debug(f"Searching knowledge base for: {query}")
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None,
            lambda: vector_index.similarity_search_with_score(query, k=RAG_TOP_K),
        )
        
        if not results:
            logger.warning("No relevant documents found, using fallback")
            return await _fallback_response(query, conversation_history)
        
        # Prepare context from retrieved documents
        context = _prepare_context(results)
        
        # Generate response with context
        response = await _generate_rag_response(
            query=query,
            context=context,
            conversation_history=conversation_history
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        # Fallback to regular GPT response
        return await _fallback_response(query, conversation_history)


def _prepare_context(results: List[tuple]) -> str:
    """
    Prepare context from search results.
    
    Args:
        results: List of (document, score) tuples
    
    Returns:
        Formatted context string
    """
    context_parts = []
    
    for i, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get('source', 'Unknown')
        content = doc.page_content.strip()
        
        context_parts.append(
            f"[Источник {i}: {source}]\n{content}\n"
        )
    
    return "\n".join(context_parts)


async def _generate_rag_response(
    query: str,
    context: str,
    conversation_history: Optional[List[Dict]] = None
) -> str:
    """
    Generate response using RAG context.
    
    Args:
        query: User's query
        context: Retrieved context from knowledge base
        conversation_history: Previous conversation
    
    Returns:
        Generated response
    """
    # Build prompt with context
    system_prompt = """Ты — DeskMate, ops-ассистент AI-студии NeiroBridge (neirobridge.ru).

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста из базы знаний
2. Если в контексте есть цены — называй их точно («от X ₽»)
3. NeiroBridge продаёт проекты и продукты, не подписку на софт
4. Если контекст не содержит ответа — честно скажи и предложи бесплатную диагностику на neirobridge.ru
5. В конце ответа укажи источник: [Источник: имя_файла]
6. Отвечай на русском, кратко и по делу

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{context}"""
    
    # Prepare messages
    messages = [
        {
            "role": "system",
            "content": system_prompt.format(context=context)
        }
    ]
    
    # Add conversation history if available
    if conversation_history:
        # Limit history to avoid token limits
        recent_history = conversation_history[-6:]  # Last 3 exchanges
        messages.extend(recent_history)
    
    # Add current query
    messages.append({
        "role": "user",
        "content": query
    })
    
    # Generate response
    response = await openai_client.generate_text_response(messages)
    
    return response


async def _fallback_response(
    query: str,
    conversation_history: Optional[List[Dict]] = None
) -> str:
    """
    Fallback to regular GPT response when RAG fails.
    
    Args:
        query: User's query
        conversation_history: Previous conversation
    
    Returns:
        Generated response
    """
    logger.info("Using fallback response (no RAG context)")
    
    system_message = {
        "role": "system",
        "content": """Ты - личный ассистент. 
        
База знаний пока пуста или не содержит информации по этому вопросу.
Ответь на основе своих общих знаний, но предупреди пользователя, 
что это не основано на специфической базе знаний."""
    }
    
    messages = [system_message]
    
    if conversation_history:
        messages.extend(conversation_history[-6:])
    
    messages.append({
        "role": "user",
        "content": query
    })
    
    response = await openai_client.generate_text_response(messages)
    
    return f"⚠️ База знаний не содержит информации по этому вопросу.\n\n{response}"


async def add_document_to_knowledge_base(file_path: str) -> dict:
    """
    Add a document to the knowledge base.
    
    Args:
        file_path: Path to document file
    
    Returns:
        Dictionary with status and details
    """
    try:
        from pathlib import Path
        from rag.loader import document_loader
        
        # Load document
        file_path = Path(file_path)
        documents = document_loader.load_document(file_path)
        
        # Add to index
        vector_index.add_documents(documents)
        
        logger.info(f"Added {file_path.name} to knowledge base")
        
        return {
            "success": True,
            "file": file_path.name,
            "chunks": len(documents),
            "message": f"Документ {file_path.name} успешно добавлен ({len(documents)} фрагментов)"
        }
        
    except Exception as e:
        logger.error(f"Error adding document to knowledge base: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Ошибка при добавлении документа: {e}"
        }


def get_knowledge_base_stats() -> dict:
    """
    Get statistics about the knowledge base.
    
    Returns:
        Dictionary with statistics
    """
    return vector_index.get_stats()

