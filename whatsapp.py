import requests
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = TOKEN = os.getenv("WA_TOKEN")
PHONE_NUMBER_ID = PHONE_ID = os.getenv("WA_PHONE_ID")

def send_whatsapp(to, message):

    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    requests.post(url, headers=headers, json=payload)
