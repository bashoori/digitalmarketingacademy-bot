import os
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ROOT_URL = os.getenv("ROOT_URL", "https://digitalmarketingacademy-bot.onrender.com")

if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN not found in environment variables!")

webhook_url = f"{ROOT_URL.rstrip('/')}/webhook/{TELEGRAM_TOKEN}"
api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}"

print(f"Setting webhook to: {webhook_url}")
response = requests.get(api_url)
print("Response:", response.status_code, response.text)
