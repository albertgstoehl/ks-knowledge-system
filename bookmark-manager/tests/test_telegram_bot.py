# tests/test_telegram_bot.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add bot to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update"""
    update = MagicMock()
    update.effective_user.id = 123456
    update.message.text = "https://example.com/article"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock context"""
    return MagicMock()


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Test /start command responds with help text"""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": ""}):
        from bot.main import start
        await start(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "URL" in call_args


@pytest.mark.asyncio
async def test_handle_url_success(mock_update, mock_context):
    """Test successful URL submission"""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": ""}):
        # Reload module to pick up env vars
        import importlib
        import bot.main
        importlib.reload(bot.main)
        from bot.main import handle_url

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"title": "Example Article"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            await handle_url(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Saved" in call_args


@pytest.mark.asyncio
async def test_handle_url_duplicate(mock_update, mock_context):
    """Test duplicate URL returns 'Already saved'"""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": ""}):
        import importlib
        import bot.main
        importlib.reload(bot.main)
        from bot.main import handle_url

        mock_response = MagicMock()
        mock_response.status_code = 409

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            await handle_url(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Already saved" in call_args


@pytest.mark.asyncio
async def test_unauthorized_user(mock_update, mock_context):
    """Test unauthorized user is rejected"""
    mock_update.effective_user.id = 999999

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": "123456"}):
        import importlib
        import bot.main
        importlib.reload(bot.main)
        from bot.main import start

        await start(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Not authorized" in call_args


@pytest.mark.asyncio
async def test_thesis_command_handler_exists():
    """Test that /thesis command is registered"""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "ALLOWED_TELEGRAM_USERS": ""}):
        import importlib
        import bot.main
        importlib.reload(bot.main)

        # Check that handle_thesis function exists
        assert hasattr(bot.main, 'handle_thesis')
