# bot/main.py
import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")
ALLOWED_USERS = os.getenv("ALLOWED_TELEGRAM_USERS", "").split(",")


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized"""
    if not ALLOWED_USERS or ALLOWED_USERS == [""]:
        return True  # No restrictions if not configured
    return str(user_id) in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    await update.message.reply_text(
        "Send me a URL to save it as a bookmark.\n\n"
        "I'll fetch the title and generate a summary automatically."
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle URL messages"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    text = update.message.text.strip()

    # Extract URL from text (handle shared URLs with titles)
    url = None
    for word in text.split():
        if word.startswith(("http://", "https://")):
            url = word
            break

    if not url:
        await update.message.reply_text("Please send a valid URL starting with http:// or https://")
        return

    # Send to API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/bookmarks",
                json={"url": url},
                timeout=30.0
            )

        if response.status_code == 201:
            data = response.json()
            title = data.get("title") or "Untitled"
            domain = url.split("/")[2].replace("www.", "")
            await update.message.reply_text(f"Saved: {title} - {domain}")
        elif response.status_code == 409:
            await update.message.reply_text("Already saved!")
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            await update.message.reply_text("Failed to save bookmark. Try again later.")
    except Exception as e:
        logger.error(f"Error saving bookmark: {e}")
        await update.message.reply_text("Failed to save bookmark. Try again later.")


async def handle_thesis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /thesis command - save or convert to thesis"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    # Extract URL from command args
    if not context.args:
        await update.message.reply_text("Usage: /thesis <url>")
        return

    url = context.args[0]
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("Please provide a valid URL")
        return

    try:
        async with httpx.AsyncClient() as client:
            # First try to create new bookmark
            response = await client.post(
                f"{API_URL}/bookmarks",
                json={"url": url},
                timeout=30.0
            )

            if response.status_code == 201:
                data = response.json()
                bookmark_id = data["id"]
            elif response.status_code == 409:
                # Already exists - get its ID
                list_response = await client.get(
                    f"{API_URL}/bookmarks",
                    params={"limit": 1000},
                    timeout=30.0
                )
                bookmarks = list_response.json()
                bookmark_id = None
                for b in bookmarks:
                    if b["url"] == url:
                        bookmark_id = b["id"]
                        break
                if not bookmark_id:
                    await update.message.reply_text("Could not find bookmark")
                    return
            else:
                await update.message.reply_text("Failed to save bookmark")
                return

            # Mark as thesis
            thesis_response = await client.patch(
                f"{API_URL}/bookmarks/{bookmark_id}/thesis",
                json={"is_thesis": True},
                timeout=30.0
            )

            if thesis_response.ok:
                data = thesis_response.json()
                title = data.get("title") or "Untitled"
                await update.message.reply_text(f"Thesis saved: {title}")
            else:
                await update.message.reply_text("Failed to mark as thesis")

    except Exception as e:
        logger.error(f"Error in /thesis command: {e}")
        await update.message.reply_text("Failed to process thesis")


async def handle_pin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pin command - save and pin bookmark"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /pin <url>")
        return

    url = context.args[0]
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("Please provide a valid URL")
        return

    try:
        async with httpx.AsyncClient() as client:
            # First try to create new bookmark
            response = await client.post(
                f"{API_URL}/bookmarks",
                json={"url": url},
                timeout=30.0
            )

            if response.status_code == 201:
                data = response.json()
                bookmark_id = data["id"]
            elif response.status_code == 409:
                # Already exists - get its ID
                list_response = await client.get(
                    f"{API_URL}/bookmarks",
                    params={"limit": 1000},
                    timeout=30.0
                )
                bookmarks = list_response.json()
                bookmark_id = None
                for b in bookmarks:
                    if b["url"] == url:
                        bookmark_id = b["id"]
                        break
                if not bookmark_id:
                    await update.message.reply_text("Could not find bookmark")
                    return
            else:
                await update.message.reply_text("Failed to save bookmark")
                return

            # Pin it
            pin_response = await client.patch(
                f"{API_URL}/bookmarks/{bookmark_id}/pin",
                json={"pinned": True},
                timeout=30.0
            )

            if pin_response.ok:
                data = pin_response.json()
                title = data.get("title") or "Untitled"
                await update.message.reply_text(f"Pinned: {title}")
            else:
                await update.message.reply_text("Failed to pin")

    except Exception as e:
        logger.error(f"Error in /pin command: {e}")
        await update.message.reply_text("Failed to pin bookmark")


def main() -> None:
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("thesis", handle_thesis))
    application.add_handler(CommandHandler("pin", handle_pin))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    # Run bot
    logger.info("Starting Telegram bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
