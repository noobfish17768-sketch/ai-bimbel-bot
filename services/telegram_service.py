import requests
import os


def set_telegram_webhook(bot_token: str, bot_id: int):
    base_url = os.getenv("BASE_URL")

    if not base_url:
        print("❌ BASE_URL not set")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    webhook_url = f"{base_url}/webhook/telegram/{bot_id}"

    try:
        response = requests.post(
            url,
            json={"url": webhook_url},
            timeout=10  # ✅ prevent hanging
        )

        data = response.json()

        if data.get("ok"):
            print(f"✅ Webhook set for bot {bot_id}")
            print(f"🔗 URL: {webhook_url}")
            return True
        else:
            print("❌ Telegram API error:")
            print(data)
            return False

    except requests.exceptions.Timeout:
        print("❌ Telegram timeout")
        return False

    except Exception as e:
        print("❌ TELEGRAM WEBHOOK ERROR:", e)
        return False