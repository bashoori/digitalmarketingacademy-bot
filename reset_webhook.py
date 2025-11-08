import requests

TOKEN = "8514680896:AAEYMMj4JG_Ujc2rAc_KszjTxSdkCVebQOo"
ROOT_URL = "https://digitalmarketingacademy-bot.onrender.com/" + TOKEN

requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={ROOT_URL}")

print("✅ Webhook reset to:", ROOT_URL)

