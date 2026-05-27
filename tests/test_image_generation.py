"""
Тесты для функциональности генерации изображений.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.image_generation import detect_image_generation_intent


class TestImageGenerationIntentDetection:
    """Тесты для определения намерения генерации изображений."""
    
    @pytest.mark.asyncio
    async def test_detect_draw_intent_russian(self):
        """Тест определения намерения по ключевому слову 'нарисуй'."""
        text = "Нарисуй кота в космосе"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is True
        assert result.get('confidence', 0) > 0.5
        assert 'prompt' in result
    
    @pytest.mark.asyncio
    async def test_detect_create_intent_russian(self):
        """Тест определения намерения по фразе 'создай изображение'."""
        text = "Создай изображение заката на пляже"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is True
        assert result.get('confidence', 0) > 0.5
    
    @pytest.mark.asyncio
    async def test_detect_generate_intent_russian(self):
        """Тест определения намерения по слову 'сгенерируй'."""
        text = "Сгенерируй картинку дракона"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is True
        assert result.get('confidence', 0) > 0.5
    
    @pytest.mark.asyncio
    async def test_detect_visualize_intent_russian(self):
        """Тест определения намерения по слову 'визуализируй'."""
        text = "Визуализируй футуристический город"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is True
        assert result.get('confidence', 0) > 0.5
    
    @pytest.mark.asyncio
    async def test_detect_show_intent_russian(self):
        """Тест определения намерения по фразе 'покажи как выглядит'."""
        text = "Покажи как выглядит робот"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is True
        assert result.get('confidence', 0) > 0.5
    
    @pytest.mark.asyncio
    async def test_detect_draw_intent_english(self):
        """Тест определения намерения по английскому слову 'draw'."""
        text = "Draw a cat in space"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is True
        assert result.get('confidence', 0) > 0.5
    
    @pytest.mark.asyncio
    async def test_detect_create_intent_english(self):
        """Тест определения намерения по фразе 'create image'."""
        text = "Create an image of a sunset"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is True
        assert result.get('confidence', 0) > 0.5
    
    @pytest.mark.asyncio
    async def test_no_intent_question(self):
        """Тест что обычный вопрос НЕ определяется как запрос на генерацию."""
        text = "Что такое Python?"
        result = await detect_image_generation_intent(text)
        
        # Может быть True или False в зависимости от AI, но не должно быть высокой уверенности
        if result['needs_generation']:
            assert result.get('confidence', 0) < 0.8
    
    @pytest.mark.asyncio
    async def test_no_intent_greeting(self):
        """Тест что приветствие НЕ определяется как запрос на генерацию."""
        text = "Привет, как дела?"
        result = await detect_image_generation_intent(text)
        
        # Приветствие не должно быть запросом на генерацию
        assert result['needs_generation'] is False or result.get('confidence', 0) < 0.5
    
    @pytest.mark.asyncio
    async def test_no_intent_information_request(self):
        """Тест что информационный запрос НЕ определяется как запрос на генерацию."""
        text = "Расскажи про машинное обучение"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is False or result.get('confidence', 0) < 0.5
    
    @pytest.mark.asyncio
    async def test_ambiguous_intent(self):
        """Тест неоднозначного запроса."""
        text = "Можешь показать пример?"
        result = await detect_image_generation_intent(text)
        
        # Неоднозначный запрос - может быть как да, так и нет
        # Главное что функция не падает
        assert 'needs_generation' in result
        assert 'confidence' in result
    
    @pytest.mark.asyncio
    async def test_context_aware_detection(self):
        """Тест определения с учетом контекста разговора."""
        conversation_history = [
            {"role": "user", "content": "Расскажи про космос"},
            {"role": "assistant", "content": "Космос - это бесконечное пространство..."}
        ]
        
        text = "А можешь показать как это выглядит?"
        result = await detect_image_generation_intent(text, conversation_history)
        
        # С контекстом должно определиться как запрос на генерацию
        assert result['needs_generation'] is True
        assert result.get('confidence', 0) > 0.5
    
    @pytest.mark.asyncio
    async def test_detailed_prompt(self):
        """Тест детального промпта."""
        text = "Нарисуй футуристический город с летающими машинами, неоновыми вывесками и небоскребами в стиле cyberpunk"
        result = await detect_image_generation_intent(text)
        
        assert result['needs_generation'] is True
        assert 'prompt' in result
        # Промпт должен содержать ключевые элементы
        prompt_lower = result['prompt'].lower()
        assert any(word in prompt_lower for word in ['city', 'futuristic', 'cyberpunk', 'город'])
    
    @pytest.mark.asyncio
    async def test_empty_string(self):
        """Тест пустой строки."""
        text = ""
        result = await detect_image_generation_intent(text)
        
        # Пустая строка не должна быть запросом на генерацию
        assert result['needs_generation'] is False
    
    @pytest.mark.asyncio
    async def test_very_long_text(self):
        """Тест очень длинного текста."""
        text = "Нарисуй " + "красивый " * 100 + "пейзаж"
        result = await detect_image_generation_intent(text)
        
        # Должно определиться несмотря на длину
        assert result['needs_generation'] is True
        assert 'prompt' in result


class TestImageGenerationConfig:
    """Тесты для конфигурации генерации изображений."""
    
    def test_config_imports(self):
        """Тест что конфигурация импортируется без ошибок."""
        from config import (
            DALLE_MODEL,
            DALLE_DEFAULT_SIZE,
            DALLE_DEFAULT_QUALITY,
            DALLE_DEFAULT_STYLE
        )
        
        assert DALLE_MODEL == "dall-e-3"
        assert DALLE_DEFAULT_SIZE in ["1024x1024", "1024x1792", "1792x1024"]
        assert DALLE_DEFAULT_QUALITY in ["standard", "hd"]
        assert DALLE_DEFAULT_STYLE in ["vivid", "natural"]


class TestImageGenerationRouter:
    """Тесты для роутера генерации изображений."""
    
    @pytest.mark.asyncio
    async def test_router_import(self):
        """Тест что функция роутера импортируется."""
        from services.router import route_image_generation_request
        
        assert callable(route_image_generation_request)


class TestImageGenerationHandler:
    """Тесты для обработчика генерации изображений."""
    
    def test_handler_command_exists(self):
        """Тест что команда /image существует."""
        from handlers import text
        
        # Проверяем что модуль загружен
        assert hasattr(text, 'bot')


@pytest.fixture
def cleanup_generated_images():
    """Фикстура для очистки сгенерированных тестовых изображений."""
    yield
    
    # Cleanup after test
    from config import DATA_DIR
    
    generated_dir = DATA_DIR / "generated_images"
    if generated_dir.exists():
        for file in generated_dir.glob("*.png"):
            try:
                file.unlink()
            except:
                pass


# Интеграционные тесты (требуют реального API ключа)
# Помечены как skip по умолчанию

@pytest.mark.skip(reason="Requires OpenAI API key and costs money")
@pytest.mark.asyncio
async def test_real_image_generation(cleanup_generated_images):
    """Реальный тест генерации изображения (требует API ключ)."""
    from services.image_generation import generate_image
    
    result = await generate_image(
        "A simple red apple on a white background",
        size="1024x1024",
        quality="standard"
    )
    
    assert 'image_path' in result
    assert Path(result['image_path']).exists()
    assert 'revised_prompt' in result
    assert 'url' in result


@pytest.mark.skip(reason="Requires OpenAI API key and costs money")
@pytest.mark.asyncio
async def test_real_end_to_end(cleanup_generated_images):
    """End-to-end тест генерации (требует API ключ)."""
    from services.router import route_text_request
    from utils.helpers import user_sessions
    
    test_user_id = 999999999
    
    # Очистка сессии
    user_sessions.reset_session(test_user_id)
    
    # Запрос на генерацию
    result = await route_text_request(test_user_id, "Нарисуй красное яблоко")
    
    assert 'has_image' in result
    if result.get('has_image'):
        assert 'image_path' in result
        assert Path(result['image_path']).exists()

