import os
import asyncio
from flask import Flask
from threading import Thread

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

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

# ----------------- WEB SERVER (KEEP ALIVE) -----------------
app = Flask(__name__)

@app.route("/health")
def health():
    return "OK", 200

def run_web():
    app.run(host="0.0.0.0", port=PORT)

Thread(target=run_web).start()

# ----------------- BOT LOGIC -----------------

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

    users.update_one({"user_id": user_id}, {"$set": {"files": user["files"]}})
    await update.message.reply_text(f"📂 Added ({len(user['files'])}/30)")

async def rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
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

    ep = user["ep"]
    for fid in user["files"]:
        file = await context.bot.get_file(fid)
        path = await file.download_to_drive()

        if user["changefileid"]:
            path = force_new_file(path)

        name = f"{user['rename']} S{user['season']}E{str(ep).zfill(2)}"
        ep += 1

        await update.message.reply_document(
            document=InputFile(path, filename=f"{name}")
        )

    users.delete_one({"user_id": user_id})
    await update.message.reply_text("✅ Done")

# ----------------- APP START -----------------

app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("rename", rename))
app_bot.add_handler(CommandHandler("changefileid", changefileid))
app_bot.add_handler(CommandHandler("process", process))
app_bot.add_handler(MessageHandler(filters.Document.ALL | filters.Video.ALL, handle_files))

app_bot.run_polling()
