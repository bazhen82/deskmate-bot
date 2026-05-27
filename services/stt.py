"""
Speech-to-Text Service.
Handles voice message transcription.
"""

from pathlib import Path
from typing import Union

from services.openai_client import openai_client
from utils.logging import logger
from utils.helpers import convert_ogg_to_wav, cleanup_file


async def transcribe_voice_message(audio_path: Union[str, Path]) -> str:
    """
    Transcribe a voice message to text.
    
    Args:
        audio_path: Path to audio file (OGG or WAV)
    
    Returns:
        Transcribed text
    """
    audio_path = Path(audio_path)
    
    try:
        # Whisper supports ogg/opus from Telegram directly
        text = await openai_client.transcribe_audio(audio_path)
        logger.info(f"Transcription completed: {len(text)} characters")
        return text
        
    except Exception as e:
        if audio_path.suffix.lower() != ".ogg":
            logger.error(f"Error in voice transcription: {e}")
            raise
        
        # Fallback: convert ogg → wav if direct upload fails
        wav_path = None
        try:
            logger.debug(f"Retrying with WAV conversion: {audio_path}")
            wav_path = convert_ogg_to_wav(audio_path)
            text = await openai_client.transcribe_audio(wav_path)
            logger.info(f"Transcription completed: {len(text)} characters")
            return text
        except Exception as e2:
            logger.error(f"Error in voice transcription: {e2}")
            raise
        finally:
            if wav_path and wav_path != audio_path:
                cleanup_file(wav_path)

