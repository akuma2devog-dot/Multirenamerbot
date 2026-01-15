import os
import asyncio
from flask import Flask
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from db.mongo import users
from utils.rename_logic import parse_rename
from utils.fileid_utils import force_new_file

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

# ================== FLASK APP ==================
app = Flask(__name__)

@app.route("/health")
def health():
    return "OK", 200

# ================== BOT LOGIC ==================

MAX_FILES = 30

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users.update_one(
        {"user_id": update.effective_user.id},
        {"$set": {
            "files": [],
            "rename": None,
            "season": 1,
            "ep": 1,
            "changefileid": False
        }},
        upsert=True
    )
    await update.message.reply_text("👋 Send up to 30 files")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users.find_one({"user_id": user_id})

    if len(user["files"]) >= MAX_FILES:
        await update.message.reply_text("❌ Max 30 files reached")
        return

    file = update.message.document or update.message.video
    user["files"].append(file.file_id)

    users.update_one(
        {"user_id": user_id},
        {"$set": {"files": user["files"]}}
    )

    await update.message.reply_text(
        f"📂 Added ({len(user['files'])}/{MAX_FILES})"
    )

async def rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("❌ Usage: /rename Naruto S1E")
        return

    base, season, ep = parse_rename(text)

    users.update_one(
        {"user_id": update.effective_user.id},
        {"$set": {
            "rename": base,
            "season": season,
            "ep": ep
        }}
    )

    await update.message.reply_text("✏️ Rename pattern saved")

async def changefileid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users.update_one(
        {"user_id": update.effective_user.id},
        {"$set": {"changefileid": True}}
    )
    await update.message.reply_text("🆔 FileID change enabled")

async def process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users.find_one({"user_id": user_id})

    if not user or not user.get("files"):
        await update.message.reply_text("❌ No files to process")
        return

    ep = user["ep"]

    for fid in user["files"]:
        tg_file = await context.bot.get_file(fid)
        path = await tg_file.download_to_drive()

        if user.get("changefileid"):
            path = force_new_file(path)

        filename = (
            f"{user['rename']} "
            f"S{user['season']}E{str(ep).zfill(2)}"
        )
        ep += 1

        await update.message.reply_document(
            document=InputFile(path, filename=filename)
        )

    users.delete_one({"user_id": user_id})
    await update.message.reply_text("✅ Done")

# ================== START BOT ==================

def start_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rename", rename))
    application.add_handler(CommandHandler("changefileid", changefileid))
    application.add_handler(CommandHandler("process", process))
    application.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.Video.ALL,
            handle_files
        )
    )

    application.run_polling()

# ================== MAIN ==================

if __name__ == "__main__":
    # Start Telegram bot in event loop
    asyncio.get_event_loop().create_task(
        asyncio.to_thread(start_bot)
    )

    # Start Flask (Render needs this)
    app.run(host="0.0.0.0", port=PORT)
