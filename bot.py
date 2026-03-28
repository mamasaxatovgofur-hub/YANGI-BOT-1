import sqlite3
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ===================== CONFIG =====================
TOKEN = "8672258475:AAEYVNVkycE-jwdJCZ3Ut1gIxTZFCxw_Aio"
ADMIN_ID = 8512949204
# ==================================================

# ===================== DATABASE ==================
conn = sqlite3.connect("movies.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    photo TEXT,
    link TEXT,
    title TEXT,
    added_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    code TEXT,
    used_at TEXT
)
""")
conn.commit()
# ==================================================

# ===================== STATES ====================
ADD_PHOTO, ADD_LINK = range(2)

def generate_code():
    return str(random.randint(1000, 9999))
# ==================================================

# ===================== HANDLERS ==================

# ---- /start ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Salom! Kod kiriting filmni olish uchun.\n\n"
        "💡 Kodsiz film ko‘ra olmaysiz!"
    )

# ---- Foydalanuvchi kodi ----
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    user_id = update.message.from_user.id

    cursor.execute("SELECT * FROM movies WHERE code=?", (code,))
    result = cursor.fetchone()

    if result:
        _, photo, link, title, added_at = result

        # Inline tugma bilan link
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📥 Linkga o‘tish", url=link)]]
        )
        caption = f"🎬 Film: {title}\n📅 Qo‘shilgan: {added_at}\n🎫 Kod: {code}"

        await update.message.reply_photo(photo=photo, caption=caption, reply_markup=keyboard)

        # Kod ishlatilgan qilib foydalanuvchi bazasiga yozish
        cursor.execute("INSERT INTO users VALUES (?, ?, ?)", (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # Kodni movies jadvalidan o'chiramiz → faqat 1 marta ishlaydi
        cursor.execute("DELETE FROM movies WHERE code=?", (code,))
        conn.commit()
    else:
        await update.message.reply_text("❌ Kod noto‘g‘ri yoki ishlatilgan! Iltimos, boshqa kod kiriting.")

# ---- Admin /add boshlanishi ----
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return ConversationHandler.END

    code = generate_code()
    context.user_data["code"] = code

    await update.message.reply_text(f"🎬 Yangi kod: {code}\nRasm yuboring:")
    return ADD_PHOTO

# ---- Admin rasm qabul qilish ----
async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Iltimos, rasm yuboring!")
        return ADD_PHOTO

    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Endi link yuboring:")
    return ADD_LINK

# ---- Admin link qabul qilish ----
async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = context.user_data["code"]
    photo = context.user_data["photo"]
    link = update.message.text
    title = f"KinoBoom #{code}"  # avtomatik title
    added_at = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("INSERT INTO movies VALUES (?, ?, ?, ?, ?)", (code, photo, link, title, added_at))
    conn.commit()

    await update.message.reply_text(f"✅ Saqlandi: {code} ({title})")
    return ConversationHandler.END

# ---- Statistika (faqat admin) ----
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT code, COUNT(*) as cnt FROM users GROUP BY code ORDER BY cnt DESC LIMIT 5")
    top_codes = cursor.fetchall()

    cursor.execute("SELECT code, title, added_at FROM movies ORDER BY added_at DESC LIMIT 5")
    latest_movies = cursor.fetchall()

    msg = f"📊 Botga kirishlar soni: {total_users}\n\n"
    msg += "🏆 Eng ko‘p ishlatilgan kodlar:\n"
    if top_codes:
        for c, cnt in top_codes:
            msg += f"{c} - {cnt} marta\n"
    else:
        msg += "Hozircha ma'lumot yo‘q\n"

    msg += "\n🆕 So‘nggi qo‘shilgan filmlar:\n"
    if latest_movies:
        for c, t, d in latest_movies:
            msg += f"{t} ({c}) - {d}\n"
    else:
        msg += "Hozircha ma'lumot yo‘q\n"

    await update.message.reply_text(msg)

# ---- Help ----
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Qo‘llanma:\n"
        "1️⃣ /start - Kod kiriting film olish uchun\n"
        "2️⃣ /add - Admin: yangi film qo‘shish\n"
        "3️⃣ /stats - Admin: statistika ko‘rish\n\n"
        "⚠️ Kodsiz film ko‘rish mumkin emas!"
    )

# ==================================================

# ===================== APPLICATION ==================
app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("add", add_start)],
    states={
        ADD_PHOTO: [MessageHandler(filters.PHOTO, add_photo)],
        ADD_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_link)],
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
app.add_handler(conv)

print("Bot ishga tushdi...")
app.run_polling()
