import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import os
import json
import time

# Load config
with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var)

API_ID = int(getenv("ID"))
API_HASH = getenv("HASH")
BOT_TOKEN = getenv("TOKEN")
STRING_SESSION = getenv("STRING")
DB_CHANNEL = int(getenv("DB_CHANNEL"))

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION) if STRING_SESSION else None
if user:
    user.start()

def extract_buttons(msg):
    if not msg.reply_markup:
        return None

    keyboard = []
    for row in msg.reply_markup.inline_keyboard:
        btn_row = []
        for btn in row:
            btn_row.append(InlineKeyboardButton(text=btn.text, url=btn.url))
        keyboard.append(btn_row)

    return InlineKeyboardMarkup(keyboard)

def get_type(msg):
    if msg.document: return "Document", msg.document.file_name, msg.document.file_size
    if msg.video: return "Video", msg.video.file_name, msg.video.file_size
    if msg.audio: return "Audio", msg.audio.file_name, msg.audio.file_size
    if msg.voice: return "Voice", "voice.ogg", msg.voice.file_size
    if msg.photo: return "Photo", "photo.jpg", 0
    if msg.animation: return "Animation", msg.animation.file_name, msg.animation.file_size
    if msg.sticker: return "Sticker", "sticker.webp", 0
    if msg.text: return "Text", None, 0
    return None, None, 0

@bot.on_message(filters.command("start"))
async def start(_, m):
    await m.reply("👋 Send Telegram post links. I’ll fetch & upload them to your DB channel.")

@bot.on_message(filters.text)
async def main(_, m):
    text = m.text.strip()
    if "https://t.me/" not in text or not user:
        return await m.reply("❌ Invalid link or no user session.")

    try:
        parts = text.split("/")
        temp = parts[-1].replace("?single", "").split("-")
        from_id = int(temp[0])
        to_id = int(temp[1]) if len(temp) > 1 else from_id
        chat_id = int("-100" + parts[4]) if "t.me/c/" in text else parts[3]

        for msg_id in range(from_id, to_id + 1):
            try:
                await forward_message(m, chat_id, msg_id)
            except Exception as e:
                await m.reply(f"❌ Error in message {msg_id}: {e}")
    except Exception as e:
        await m.reply(f"❌ Invalid format: {e}")

async def forward_message(m, chat_id, msg_id):
    msg = await user.get_messages(chat_id, msg_id)
    markup = extract_buttons(msg)
    msg_type, filename, filesize = get_type(msg)

    try:
        if msg_type == "Text" or not msg_type:
            sent = await user.send_message(
                DB_CHANNEL,
                msg.text or msg.caption or "",
                entities=msg.entities
            )
        else:
            send_func = {
                "Document": user.send_document,
                "Video": user.send_video,
                "Audio": user.send_audio,
                "Photo": user.send_photo,
                "Voice": user.send_voice,
                "Animation": user.send_animation,
                "Sticker": user.send_sticker,
            }.get(msg_type)

            sent = await send_func(
                DB_CHANNEL,
                msg.media.file_id,
                caption=msg.caption or "",
                caption_entities=msg.caption_entities
            )

        if markup:
            if msg_type == "Text":
                await bot.edit_message_text(
                    DB_CHANNEL,
                    sent.id,
                    sent.text,
                    entities=sent.entities,
                    reply_markup=markup
                )
            else:
                await bot.edit_message_caption(
                    DB_CHANNEL,
                    sent.id,
                    caption=sent.caption or "",
                    caption_entities=sent.caption_entities,
                    reply_markup=markup
                )
    except Exception as e:
        await m.reply(f"❌ Failed: {e}")

bot.run()

