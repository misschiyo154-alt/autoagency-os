import os
import asyncio

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN missing in .env")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    print(f"\n✅ Telegram connected!")
    print(f"📌 CHAT_ID = {chat_id}\n")

    await update.message.reply_text(
        "🤖 AOS Executive online.\n\n"
        "Ready for instructions, Boss."
    )


def main():
    print("🤖 Starting AOS Executive...")
    print("Send /start to your bot on Telegram.\n")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.run_polling()


if __name__ == "__main__":
    main()