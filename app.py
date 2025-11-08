import os, re, json, requests, asyncio, random
from datetime import datetime, timezone
from flask import Flask, request as flask_request
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
from telegram.request import HTTPXRequest

# ========== ENV CONFIG ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ROOT_URL = os.getenv("ROOT_URL", "https://digitalmarketingacademy-bot.onrender.com")
PORT = int(os.getenv("PORT", "10000"))
GOOGLE_SHEET_WEBAPP_URL = os.getenv("GOOGLE_SHEET_WEBAPP_URL")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@BitaDigitalSupport")

if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN not set")

# ========== STORAGE ==========
LEADS_FILE = "leads.json"
def load_leads():
    if not os.path.exists(LEADS_FILE):
        return []
    try:
        return json.load(open(LEADS_FILE, "r", encoding="utf-8"))
    except Exception:
        return []

def save_leads(leads):
    json.dump(leads, open(LEADS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def user_has_email(user_id):
    leads = load_leads()
    return any(str(l.get("user_id")) == str(user_id) for l in leads)

# ========== HELPERS ==========
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
def normalize_email(s): return s.replace("\u200c","").replace("\u200f","").strip().lower()
def is_valid_email(e): return EMAIL_RE.match(e) if e else False

def post_to_sheet(payload):
    if not GOOGLE_SHEET_WEBAPP_URL:
        return False
    try:
        r = requests.post(GOOGLE_SHEET_WEBAPP_URL, json=payload, timeout=10)
        print(f"📤 POST Sheet → {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print("❌ post_to_sheet error:", e)
        return False

# ========== MENU ==========
MAIN_MENU = ReplyKeyboardMarkup(
    [["🏁 شروع", "📘 درباره ما"],
     ["📝 ثبت‌نام", "🎓 آموزش رایگان"],
     ["💼 فرانچایز", "📅 رزرو جلسه"],
     ["📚 منابع رایگان", "🎁 هدیه ویژه"],
     ["💬 پشتیبانی"]],
    resize_keyboard=True
)

ASK_NAME, ASK_EMAIL = range(2)

# ========== HANDLERS ==========
async def show_menu(update, ctx):
    await update.message.reply_text(
        "👋 سلام! به ربات دیجیتال مارکتینگ خوش آمدید.\nاز منوی زیر انتخاب کنید:",
        reply_markup=MAIN_MENU)

async def about(update, ctx):
    await update.message.reply_text(
        "📘 *درباره ما:*\nما آموزش و راه‌اندازی بیزنس آنلاین و فرانچایز را برای همه ساده کرده‌ایم.",
        parse_mode="Markdown", reply_markup=MAIN_MENU)

# === ثبت نام ===
async def start_registration(update, ctx):
    await update.message.reply_text("📝 لطفاً نام کامل خود را وارد کنید:",
                                    reply_markup=ReplyKeyboardRemove())
    return ASK_NAME

async def ask_name(update, ctx):
    ctx.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "خوب 🌟 حالا لطفاً ایمیل خود را وارد کنید یا روی ❌ انصراف بزن:",
        reply_markup=ReplyKeyboardMarkup([["❌ انصراف"]], resize_keyboard=True))
    return ASK_EMAIL

async def ask_email(update, ctx):
    text = normalize_email(update.message.text)
    if text == "❌ انصراف":
        await update.message.reply_text("⛔️ ثبت‌نام لغو شد.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    if not is_valid_email(text):
        await update.message.reply_text("❌ ایمیل معتبر نیست، دوباره وارد کنید یا انصراف دهید.")
        return ASK_EMAIL

    lead = {
        "name": ctx.user_data["name"],
        "email": text,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    leads = load_leads(); leads.append(lead); save_leads(leads)
    post_to_sheet(lead)

    await update.message.reply_text(
        f"✅ {lead['name']}، ثبت‌نام شما با موفقیت انجام شد!",
        reply_markup=MAIN_MENU)
    return ConversationHandler.END

# === منوهای آموزشی ===
async def free_course(update, ctx):
    await update.message.reply_text(
        "🎓 آموزش پایه: سه مرحله برای شروع دیجیتال مارکتینگ",
        reply_markup=MAIN_MENU)

async def franchise(update, ctx):
    await update.message.reply_text(
        "💼 مدل فرانچایز یعنی همکاری با برند ما برای فروش محصولات و کسب درآمد.",
        reply_markup=MAIN_MENU)

async def appointment(update, ctx):
    await update.message.reply_text(
        "📅 برای رزرو جلسه رایگان:\n👉 https://calendly.com/your-link",
        reply_markup=MAIN_MENU)

# === فقط برای کاربران ثبت‌شده ===
async def resources(update, ctx):
    if not user_has_email(update.effective_user.id):
        await update.message.reply_text("🔒 این بخش فقط برای کاربران ثبت‌نام‌کرده در دسترس است.",
                                        reply_markup=MAIN_MENU)
        return
    await update.message.reply_text(
        "📚 منابع رایگان:\n- ویدیوها: https://youtube.com/@BitaDigital\n- فایل‌ها: https://bitadigitalhub.com/resources",
        reply_markup=MAIN_MENU)

async def gift(update, ctx):
    if not user_has_email(update.effective_user.id):
        await update.message.reply_text("🎁 این هدیه مخصوص کاربران ثبت‌نام‌کرده است.",
                                        reply_markup=MAIN_MENU)
        return
    await update.message.reply_text("🎉 هدیه ویژه شما: https://bitadigitalhub.com/gift",
                                    reply_markup=MAIN_MENU)

# === نکات روز ===
TIPS = [
    "📈 تمرکز روی ارزش محتوا مهم‌تر از تبلیغاته.",
    "💬 با مخاطب مثل دوست حرف بزن، نه مشتری.",
    "🎯 ساده بنویس، ولی مؤثر.",
]
async def daily_tip(update, ctx):
    await update.message.reply_text(random.choice(TIPS), reply_markup=MAIN_MENU)

# === پشتیبانی ===
async def support(update, ctx):
    await update.message.reply_text(
        f"💬 برای ارتباط با پشتیبانی پیام بده به: {SUPPORT_USERNAME}",
        reply_markup=MAIN_MENU)

# ========== TELEGRAM APP ==========
application = Application.builder().token(TELEGRAM_TOKEN).request(
    HTTPXRequest(read_timeout=60, connect_timeout=30)
).build()

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^(📝 ثبت‌نام|ثبت نام)$"), start_registration)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
    },
    fallbacks=[]
)

application.add_handler(conv_handler)
application.add_handler(CommandHandler("start", show_menu))
application.add_handler(MessageHandler(filters.Regex("^(🏁 شروع|🏁 منو اصلی)$"), show_menu))
application.add_handler(MessageHandler(filters.Regex("^(📘 درباره ما)$"), about))
application.add_handler(MessageHandler(filters.Regex("^(🎓 آموزش رایگان)$"), free_course))
application.add_handler(MessageHandler(filters.Regex("^(💼 فرانچایز)$"), franchise))
application.add_handler(MessageHandler(filters.Regex("^(📅 رزرو جلسه)$"), appointment))
application.add_handler(MessageHandler(filters.Regex("^(📚 منابع رایگان)$"), resources))
application.add_handler(MessageHandler(filters.Regex("^(🎁 هدیه ویژه)$"), gift))
application.add_handler(MessageHandler(filters.Regex("^(💬 پشتیبانی)$"), support))
application.add_handler(MessageHandler(filters.Regex("^(💡 نکات روز)$"), daily_tip))

# ========== FLASK & WEBHOOK ==========
flask_app = Flask(__name__)
loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)

@flask_app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = flask_request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    loop.run_until_complete(application.process_update(update))
    return "ok", 200

@flask_app.route("/", methods=["GET"])
def index():
    return f"✅ Bot running — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"

def set_webhook():
    loop.run_until_complete(application.initialize())
    url = f"{ROOT_URL.rstrip('/')}/webhook/{TELEGRAM_TOKEN}"
    loop.run_until_complete(application.bot.set_webhook(url))
    print(f"✅ Webhook set to {url}")

set_webhook()

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=PORT)
