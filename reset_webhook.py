import requests

TOKEN = "8514680896:AAEYMMj4JG_Ujc2rAc_KszjTxSdkCVebQOo"
WEBHOOK_URL = "https://digitalmarketingacademy-bot.onrender.com/" + TOKEN

requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")

print("✅ Webhook reset to:", WEBHOOK_URL)

