import os
import sys

import requests
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN missing in .env")
    sys.exit(1)

if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID missing in .env")
    sys.exit(1)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(data)

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print('python telegram_notify.py "Your message"')
        sys.exit(1)

    message = " ".join(sys.argv[1:])

    try:
        send_telegram(message)
        print("✅ Telegram notification sent")

    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram HTTP Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()