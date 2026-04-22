import requests
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = TOKEN = os.getenv("WA_TOKEN")
PHONE_NUMBER_ID = PHONE_ID = os.getenv("WA_PHONE_ID")
TO_NUMBER = "6281882882224"  # nomor tujuan (format internasional, tanpa +)

url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"

headers = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json"
}

data = {
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": TO_NUMBER,
    "type": "text",
    "text": {
        "body": "Hello dari Python 🚀"
    }
}

response = requests.post(url, headers=headers, json=data)

print("Status:", response.status_code)
print("Response:", response.text)