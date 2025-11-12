import os
import re
import json
import requests
import asyncio
from datetime import datetime, timezone
from flask import Flask, request as flask_request
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

# ========== ENV CONFIG ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_SHEET_WEBAPP_URL = os.getenv("GOOGLE_SHEET_WEBAPP_URL")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@support")
ROOT_URL = os.getenv("ROOT_URL", "https://digitalmarketingacademy-bot.onrender.com")
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN is not set!")

# ========== STORAGE ==========
LEADS_FILE = "leads.json"

def load_leads():
    if not os.path.exists(LEADS_FILE):
        return []
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_leads(leads):
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

# ========== HELPERS ==========
def normalize_email(raw: str) -> str:
    if not raw:
        return ""
    return raw.replace("\u200c", "").replace("\u200f", "").strip().lower()

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
def is_valid_email(email: str) -> bool:
    return EMAIL_RE.match(email.strip()) if email else False

def post_to_sheet(payload: dict, timeout: int = 10) -> bool:
    """Send lead data to Google Sheet Web App."""
    if not GOOGLE_SHEET_WEBAPP_URL:
        print("⚠️ GOOGLE_SHEET_WEBAPP_URL not set")
        return False
    try:
        r = requests.post(GOOGLE_SHEET_WEBAPP_URL, json=payload, timeout=timeout)
        print(f"📤 POST Sheet → {r.status_code}: {r.text[:200]}")
        return r.status_code == 200
    except Exception as e:
        print("❌ post_to_sheet error:", e)
        return False

# ========== MENUS ==========
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🏁 شروع", "📘 درباره ما"],
        ["📝 دریافت اطلاعات", "🎓 آموزش رایگان"],
        ["💼 فرانچایز", "💬 پشتیبانی"],
    ],
    resize_keyboard=True,
)

# ========== STATES ==========
ASK_NAME, ASK_EMAIL = range(2)

# ========== HANDLERS ==========
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام! به ربات دیجیتال مارکتینگ خوش آمدید.\n\nاز منوی زیر انتخاب کنید:",
        reply_markup=MAIN_MENU,
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 *درباره ما:*\nما آموزش و راه‌اندازی بیزنس آنلاین، اتوماسیون و دیجیتال مارکتینگ را "
        "برای همه ساده کرده‌ایم. با ما یاد بگیرید چطور برند خودتان را بسازید و درآمد آنلاین کسب کنید.",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU,
    )

# === Registration ===
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📥 user clicked: {update.message.text!r}")
    await update.message.reply_text("📝 لطفاً نام کامل خود را وارد کنید:", reply_markup=ReplyKeyboardRemove())
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("خوب 🌟 حالا لطفاً ایمیل خود را وارد کنید:")
    return ASK_EMAIL

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = normalize_email(update.message.text)
    name = context.user_data.get("name", "")

    if not is_valid_email(email):
        await update.message.reply_text("❌ ایمیل معتبر نیست. دوباره وارد کنید:")
        return ASK_EMAIL

    lead = {
        "name": name,
        "email": email,
        "user_id": update.effective_user.id if update.effective_user else None,
        "username": update.effective_user.username if update.effective_user else None,
        "status": "Validated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    leads = load_leads()
    leads.append(lead)
    save_leads(leads)

    posted = post_to_sheet(lead)
    text = f"✅ {name}، ثبت‌نام شما انجام شد!" if posted else "✅ ثبت‌نام انجام شد (ذخیره محلی موفق)."

    await update.message.reply_text(
        text + "\n\n🎓 حالا می‌خوای آموزش رایگان شروع دیجیتال مارکتینگ رو ببینی؟",
        reply_markup=ReplyKeyboardMarkup([["🎓 بریم سراغ آموزش", "🏁 منو اصلی"]], resize_keyboard=True),
    )
    return ConversationHandler.END

# === Education & Franchise ===
async def start_learning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 *مرحله ۱: چرا الان بهترین زمان شروعه؟*\n"
        "چون بازار آنلاین در حال انفجاره! برندهایی موفق می‌شن که زودتر شروع کنن.\n\nمی‌خوای بری مرحله بعد؟",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["➡️ مرحله ۲", "🏁 منو اصلی"]], resize_keyboard=True),
    )

async def learning_step2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 *مرحله ۲: مدل فرانچایز دیجیتال مارکتینگ چیه؟*\n"
        "ما بهت آموزش می‌دیم چطور با تبلیغات و فروش دیجیتال، محصولات شرکت اسپانسر رو بفروشی و پورسانت بگیری.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["➡️ مرحله ۳", "🏁 منو اصلی"]], resize_keyboard=True),
    )

async def learning_step3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 *مرحله ۳: چطور درآمدت رو بسازی؟*\n"
        "با ما یاد می‌گیری چطور محتوا تولید کنی، کمپین اجرا کنی و درآمد واقعی آنلاین بسازی.\n\nمی‌خوای جلسه رایگان مشاوره رزرو کنی؟ 📅",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["📅 رزرو جلسه", "🏁 منو اصلی"]], resize_keyboard=True),
    )

async def franchise_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 *فرانچایز چیست؟*\nاین مدل همکاری بهت اجازه می‌ده از برند و سیستم آموزشی ما استفاده کنی، "
        "محصولات رو بفروشی و از هر فروش پورسانت بگیری.\n\n📈 با ما یاد می‌گیری چطور بیزنس آنلاین بسازی بدون اینکه از صفر شروع کنی!",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU,
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💬 برای ارتباط با پشتیبانی پیام بده به: {SUPPORT_USERNAME}",
        reply_markup=ReplyKeyboardMarkup([["🏁 منو اصلی"]], resize_keyboard=True),
    )

async def appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📅 برای رزرو جلسه رایگان وارد لینک شو:\nhttps://calendly.com/bitadigital",
        reply_markup=MAIN_MENU,
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 pong — bot is alive and connected.")

# ========== TELEGRAM APPLICATION ==========
telegram_request = HTTPXRequest(connect_timeout=30, read_timeout=60, write_timeout=30, pool_timeout=30)
application = Application.builder().token(TELEGRAM_TOKEN).request(telegram_request).build()

# === Conversation: دریافت اطلاعات ===
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(r"📝\s*دریافت\s*اطلاعات"), start_registration)],
    states={ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)]},
    fallbacks=[],
)
application.add_handler(conv_handler)
application.add_handler(CommandHandler("start", show_menu))
application.add_handler(CommandHandler("ping", ping))

# === MENU MAP (resilient regex) ===
menu_map = {
    r"🏁\s*(شروع|منو\s*اصلی)": show_menu,
    r"📘\s*درباره\s*ما": about,
    r"(🎓\s*(آموزش\s*رایگان|بریم\s*سراغ\s*آموزش))": start_learning,
    r"➡️\s*مرحله\s*۲": learning_step2,
    r"➡️\s*مرحله\s*۳": learning_step3,
    r"💼\s*فرانچایز": franchise_info,
    r"💬\s*پشتیبانی": support,
    r"📅\s*رزرو\s*جلسه": appointment,
}
for pattern, handler in menu_map.items():
    application.add_handler(MessageHandler(filters.Regex(pattern), handler))
    print(f"🔗 Registered menu handler for: {pattern}")

# ========== FLASK & WEBHOOK ==========
flask_app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@flask_app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Main Telegram webhook endpoint (sync-safe)."""
    try:
        data = flask_request.get_json(force=True)
        print("📦 RAW UPDATE:", json.dumps(data, ensure_ascii=False))
        update = Update.de_json(data, application.bot)
        loop.run_until_complete(asyncio.wait_for(application.process_update(update), timeout=60))
        print("✅ Processed update successfully.")
        return "ok", 200
    except asyncio.TimeoutError:
        print("⚠️ Telegram update took too long — skipped.")
        return "timeout", 200
    except Exception as e:
        print("❌ Webhook error:", e)
        return "error", 500

@flask_app.route("/", methods=["GET"])
def index():
    return f"✅ Bot running — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"

@flask_app.route("/healthz", methods=["GET"])
def health_check():
    return {"status": "ok", "service": "digitalmarketingacademy-bot"}, 200

def set_webhook():
    """Initialize bot & set webhook."""
    try:
        loop.run_until_complete(application.initialize())
        webhook_url = f"{ROOT_URL.rstrip('/')}/webhook/{TELEGRAM_TOKEN}"
        loop.run_until_complete(asyncio.wait_for(application.bot.set_webhook(webhook_url), timeout=60))
        print(f"✅ Webhook set to {webhook_url}")
    except Exception as e:
        print("⚠️ Webhook setup failed:", e)

set_webhook()

if __name__ == "__main__":
    print("🚀 Starting Digital Marketing Academy Bot ...")
    flask_app.run(host="0.0.0.0", port=PORT)
