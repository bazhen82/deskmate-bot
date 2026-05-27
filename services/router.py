"""
Request Router.
Routes different types of requests to appropriate handlers.
"""

from typing import Dict, Any, Optional
from pathlib import Path

from services.openai_client import openai_client
from services.stt import transcribe_voice_message
from services.tts import generate_voice_response
from services.vision import analyze_image
from services.image_generation import detect_image_generation_intent, generate_image
from utils.logging import logger
from utils.helpers import user_sessions
from config import BotMode, DALLE_DEFAULT_SIZE, DALLE_DEFAULT_QUALITY


async def route_text_request(
    user_id: int,
    text: str,
    mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Route text request to appropriate handler.
    
    Args:
        user_id: User ID
        text: User's text message
        mode: Bot mode (text, rag, etc.)
    
    Returns:
        Response dictionary with 'text' and optional 'voice_path' and 'image_path'
    """
    try:
        # Determine mode
        if mode is None:
            mode = user_sessions.get_mode(user_id)
        
        # Get conversation history
        history = user_sessions.get_history(user_id)
        
        # Skip image-intent detection in RAG mode (extra API call + delay)
        if mode != BotMode.RAG:
            image_intent = await detect_image_generation_intent(text, history)
            
            if image_intent.get('needs_generation') and image_intent.get('confidence', 0) > 0.5:
                logger.info(f"Image generation request detected for user {user_id}")
                return await route_image_generation_request(
                    user_id=user_id,
                    prompt=image_intent.get('prompt', text),
                    original_text=text
                )
        
        # Add user message to history
        user_sessions.add_message(user_id, "user", text)
        
        # Route based on mode
        if mode == BotMode.RAG:
            # Use RAG for knowledge base queries
            from rag.query import query_knowledge_base
            response_text = await query_knowledge_base(text, history)
        else:
            # Standard GPT response
            messages = history + [{"role": "user", "content": text}]
            response_text = await openai_client.generate_text_response(messages)
        
        # Add assistant response to history
        user_sessions.add_message(user_id, "assistant", response_text)
        
        logger.info(f"Text request processed for user {user_id}")
        return {
            "text": response_text,
            "mode": mode
        }
        
    except Exception as e:
        logger.error(f"Error routing text request: {e}")
        return {
            "text": "Извините, произошла ошибка при обработке запроса.",
            "error": str(e)
        }


async def route_voice_request(
    user_id: int,
    voice_path: Path
) -> Dict[str, Any]:
    """
    Route voice request: transcribe, process, and generate voice response.
    
    Args:
        user_id: User ID
        voice_path: Path to voice message file
    
    Returns:
        Response dictionary with 'text', 'transcription', 'voice_path', and optional 'image_path'
    """
    try:
        # Transcribe voice to text
        logger.debug(f"Transcribing voice for user {user_id}")
        transcription = await transcribe_voice_message(voice_path)
        logger.info(f"Transcribed voice for user {user_id}: {transcription[:80]}...")
        
        # Process text request (respects RAG / text mode)
        text_response = await route_text_request(user_id, transcription)
        
        # Check if response contains an image
        if text_response.get('has_image'):
            # If image was generated, return without voice response
            logger.info(f"Voice request with image generation for user {user_id}")
            return {
                "text": text_response["text"],
                "transcription": transcription,
                "has_image": True,
                "image_path": text_response.get("image_path"),
                "revised_prompt": text_response.get("revised_prompt"),
                "voice_path": None
            }
        
        # In RAG mode — text answer only (faster, fewer API calls)
        mode = user_sessions.get_mode(user_id)
        if mode == BotMode.RAG:
            logger.info(f"Voice request (RAG mode, text only) for user {user_id}")
            return {
                "text": text_response["text"],
                "transcription": transcription,
                "voice_path": None,
                "has_image": False,
            }
        
        # Generate voice response for normal text
        user_voice = user_sessions.get_voice(user_id)
        logger.debug(f"Generating voice response with voice: {user_voice}")
        voice_response_path = await generate_voice_response(
            text_response["text"],
            voice=user_voice
        )
        
        logger.info(f"Voice request processed for user {user_id}")
        return {
            "text": text_response["text"],
            "transcription": transcription,
            "voice_path": voice_response_path,
            "has_image": False
        }
        
    except Exception as e:
        logger.error(f"Error routing voice request: {e}")
        return {
            "text": "Извините, произошла ошибка при обработке голосового сообщения.",
            "error": str(e)
        }


async def route_image_request(
    user_id: int,
    image_path: Optional[Path] = None,
    image_url: Optional[str] = None,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Route image request: analyze image with Vision API.
    
    Args:
        user_id: User ID
        image_path: Local path to image
        image_url: URL to image
        caption: Optional caption/question about image
    
    Returns:
        Response dictionary with 'text' (analysis result)
    """
    try:
        # Prepare custom prompt if caption provided
        custom_prompt = None
        if caption:
            custom_prompt = f"{caption}\n\nПроанализируй изображение с учетом этого вопроса."
        
        # Analyze image
        logger.debug(f"Analyzing image for user {user_id}")
        analysis = await analyze_image(
            image_path=image_path,
            image_url=image_url,
            custom_prompt=custom_prompt
        )
        
        # Add to conversation history
        context = f"[Пользователь отправил изображение]"
        if caption:
            context += f" с подписью: {caption}"
        user_sessions.add_message(user_id, "user", context)
        user_sessions.add_message(user_id, "assistant", analysis)
        
        logger.info(f"Image request processed for user {user_id}")
        return {
            "text": analysis
        }
        
    except Exception as e:
        logger.error(f"Error routing image request: {e}")
        return {
            "text": "Извините, произошла ошибка при анализе изображения.",
            "error": str(e)
        }


async def route_rag_request(
    user_id: int,
    query: str
) -> Dict[str, Any]:
    """
    Route RAG request: query knowledge base.
    
    Args:
        user_id: User ID
        query: User's query
    
    Returns:
        Response dictionary with 'text' and 'sources'
    """
    try:
        from rag.query import query_knowledge_base
        
        # Get conversation history
        history = user_sessions.get_history(user_id)
        
        # Query knowledge base
        logger.debug(f"Querying knowledge base for user {user_id}")
        response = await query_knowledge_base(query, history)
        
        # Add to history
        user_sessions.add_message(user_id, "user", query)
        user_sessions.add_message(user_id, "assistant", response)
        
        logger.info(f"RAG request processed for user {user_id}")
        return {
            "text": response,
            "mode": "rag"
        }
        
    except Exception as e:
        logger.error(f"Error routing RAG request: {e}")
        # Fallback to regular text response
        return await route_text_request(user_id, query, mode=BotMode.TEXT)


async def route_image_generation_request(
    user_id: int,
    prompt: str,
    original_text: str,
    size: str = DALLE_DEFAULT_SIZE,
    quality: str = DALLE_DEFAULT_QUALITY,
) -> Dict[str, Any]:
    """
    Route image generation request via GPT Image API.
    
    Args:
        user_id: User ID
        prompt: Processed prompt for image generation
        original_text: Original user text
        size: Image size (1024x1024, 1536x1024, 1024x1536, auto)
        quality: Image quality (low, medium, high, auto)
    
    Returns:
        Response dictionary with 'text', 'image_path', and generation details
    """
    try:
        logger.info(f"Generating image for user {user_id}: {prompt[:100]}...")
        
        # Generate image
        result = await generate_image(
            prompt=prompt,
            size=size,
            quality=quality,
        )
        
        # Prepare response text
        response_text = f"🎨 Изображение создано!\n\n"
        
        if result['revised_prompt'] != result['original_prompt']:
            response_text += f"**Улучшенный промпт:**\n{result['revised_prompt']}\n\n"
        
        response_text += "Вот что получилось:"
        
        # Add to conversation history
        user_sessions.add_message(user_id, "user", f"[Запрос на генерацию изображения: {original_text}]")
        user_sessions.add_message(
            user_id, 
            "assistant", 
            f"[Изображение создано: {result['revised_prompt'][:100]}...]"
        )
        
        logger.info(f"Image generation completed for user {user_id}")
        return {
            "text": response_text,
            "image_path": result['image_path'],
            "revised_prompt": result['revised_prompt'],
            "original_prompt": result['original_prompt'],
            "has_image": True
        }
        
    except Exception as e:
        logger.error(f"Error routing image generation request: {e}")
        
        # Add error to history
        user_sessions.add_message(user_id, "user", f"[Запрос на генерацию изображения: {original_text}]")
        
        error_message = "❌ Извините, произошла ошибка при генерации изображения. "
        
        if "billing" in str(e).lower() or "quota" in str(e).lower():
            error_message += "Возможно, исчерпан лимит API. Проверьте баланс OpenAI."
        elif "content_policy" in str(e).lower():
            error_message += "Запрос нарушает политику контента OpenAI."
        else:
            error_message += f"Попробуйте еще раз или перефразируйте запрос."
        
        user_sessions.add_message(user_id, "assistant", error_message)
        
        return {
            "text": error_message,
            "error": str(e),
            "has_image": False
        }

