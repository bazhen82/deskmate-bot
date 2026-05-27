"""
OpenAI Client for the Personal Assistant Bot.
Provides methods for text generation, vision, STT, and TTS.
"""

from typing import List, Dict, Optional
from openai import AsyncOpenAI
from pathlib import Path

from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    USE_PROXYAPI,
    GPT_MODEL,
    WHISPER_MODEL,
    TTS_MODEL,
    VISION_MODEL,
    TEMPERATURE,
    MAX_TOKENS
)
from utils.logging import logger


class OpenAIClient:
    """Async client for OpenAI API operations."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        
        if USE_PROXYAPI:
            logger.info(f"OpenAI client initialized with ProxyAPI: {OPENAI_BASE_URL}")
        else:
            logger.info("OpenAI client initialized with direct API")
        
        self.use_proxyapi = USE_PROXYAPI
    
    async def generate_text_response(
        self,
        messages: List[Dict[str, str]],
        model: str = GPT_MODEL,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS
    ) -> str:
        """
        Generate text response using GPT model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use
            temperature: Response randomness (0-2)
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated text response
        """
        try:
            logger.debug(f"Generating text response with {model}")
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = response.choices[0].message.content
            logger.info(f"Generated response: {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Error generating text response: {e}")
            raise
    
    async def analyze_image(
        self,
        image_url: str,
        prompt: str = "Опиши это изображение подробно. Что ты видишь?",
        model: str = VISION_MODEL
    ) -> str:
        """
        Analyze an image using GPT-4 Vision.
        
        Args:
            image_url: URL or base64 encoded image
            prompt: Analysis prompt
            model: Vision model to use
        
        Returns:
            Image analysis result
        """
        try:
            logger.debug(f"Analyzing image with {model}")
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=MAX_TOKENS
            )
            
            result = response.choices[0].message.content
            logger.info(f"Image analyzed: {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            raise
    
    async def transcribe_audio(
        self,
        audio_file_path: Path,
        model: str = WHISPER_MODEL
    ) -> str:
        """
        Transcribe audio file to text using Whisper.
        
        Args:
            audio_file_path: Path to audio file
            model: Whisper model to use
        
        Returns:
            Transcribed text
        """
        try:
            logger.debug(f"Transcribing audio: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    response_format="text"
                )
            
            logger.info(f"Audio transcribed: {len(response)} characters")
            return response
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    async def generate_speech(
        self,
        text: str,
        voice: str = "alloy",
        model: str = TTS_MODEL,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate speech from text using TTS.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, nova, fable, onyx, shimmer)
            model: TTS model to use
            output_path: Path to save audio file
        
        Returns:
            Path to generated audio file
        """
        try:
            logger.debug(f"Generating speech with voice: {voice}")
            
            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            
            # Default output path
            if output_path is None:
                from config import DATA_DIR
                import uuid
                output_path = DATA_DIR / f"tts_{uuid.uuid4()}.mp3"
            
            # Save audio to file
            response.stream_to_file(str(output_path))
            
            logger.info(f"Speech generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise


# Global client instance
openai_client = OpenAIClient()

