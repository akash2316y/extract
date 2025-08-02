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

ANIMATION_FRAMES = [".", "..", "..."]

# Initialize bot
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION) if STRING_SESSION else None
if user:
    user.start()

def humanbytes(size):
    power = 2**10
    n = 0
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def time_formatter(ms):
    seconds = int(ms / 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

def progress_bar(current, total):
    try:
        current = float(current)
        total = float(total)
        percent = current * 100 / total if total else 0
        filled = int(percent // 10)
        bar = "▪️" * filled + "▫️" * (10 - filled)
        return bar, percent
    except:
        return "▫️" * 10, 0

async def update_progress(message, current_func, total, start, status, filename="File", anim=[0]):
    while True:
        current = current_func()
        bar, percent = progress_bar(current, total)
        elapsed = time.time() - start
        speed = current / elapsed if elapsed else 0
        eta = (total - current) / speed if speed else 0
        dots = ANIMATION_FRAMES[anim[0] % len(ANIMATION_FRAMES)]

        text = f"""{status} {dots}

📄 **{filename}**
[{bar}]
Progress: {percent:.2f}%
Size: {humanbytes(current)} of {humanbytes(total)}
Speed: {humanbytes(speed)}/s
ETA: {time_formatter(eta * 1000)}"""

        try:
            await message.edit_text(text)
        except:
            pass

        if current >= total:
            break
        anim[0] += 1
        await asyncio.sleep(3)

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
    await m.reply("<blockquote>👋 Send Telegram post links. I’ll fetch & upload them to your DB channel.</blockquote>")

@bot.on_message(filters.text)
async def main(_, m):
    text = m.text.strip()
    if ("t.me/+" in text or "joinchat/" in text) and user:
        try:
            await user.join_chat(text)
            await m.reply("✅ Joined the group/channel.")
        except Exception as e:
            await m.reply(f"❌ Couldn't join: {e}")
        return

    if "https://t.me/" in text:
        try:
            parts = text.split("/")
            temp = parts[-1].replace("?single", "").split("-")
            from_id = int(temp[0])
            to_id = int(temp[1]) if len(temp) > 1 else from_id
            chat_id = int("-100" + parts[4]) if "t.me/c/" in text else parts[3]

            for msg_id in range(from_id, to_id + 1):
                try:
                    msg = await (user.get_messages if user else bot.get_messages)(chat_id, msg_id)
                    await forward_message(m, chat_id, msg_id)
                except Exception as e:
                    await m.reply(f"❌ Failed to process message {msg_id}: {e}")
        except Exception as e:
            await m.reply(f"❌ Error: {e}")

def extract_buttons(msg):
    buttons = []
    if msg.reply_markup and msg.reply_markup.inline_keyboard:
        for row in msg.reply_markup.inline_keyboard:
            new_row = []
            for btn in row:
                if btn.url:
                    new_row.append(InlineKeyboardButton(btn.text, url=btn.url))
            if new_row:
                buttons.append(new_row)
    return InlineKeyboardMarkup(buttons) if buttons else None

async def forward_message(m, chat_id, msg_id):
    if not user:
        await m.reply("❌ User session required.")
        return

    try:
        msg = await user.get_messages(chat_id, msg_id)
    except Exception as e:
        await m.reply(f"❌ Cannot fetch original message: {e}")
        return

    msg_type, filename, filesize = get_type(msg)
    markup = extract_buttons(msg)

    if msg_type == "Text" or not msg_type:
        try:
            text = (msg.text or "").strip()
            if not text and msg.reply_to_message and msg.reply_to_message.text:
                text = msg.reply_to_message.text.strip()
            if not text and msg.caption:
                text = msg.caption.strip()
            if msg.forward_from:
                sender = f"{msg.forward_from.first_name} {msg.forward_from.last_name or ''}".strip()
                text = f"💬 Forwarded from {sender}:\n\n{text}"
            elif msg.forward_sender_name:
                text = f"💬 Forwarded from {msg.forward_sender_name}:\n\n{text}"

            if text:
                await user.send_message(DB_CHANNEL, text, entities=msg.entities, reply_markup=markup)
        except:
            pass
        return

    smsg = await m.reply("📥 Downloading...")
    downloaded = [0]
    start_time = time.time()

    async def download_cb(current, total):
        downloaded[0] = current

    progress_task = asyncio.create_task(update_progress(
        smsg, lambda: downloaded[0], filesize or 1, start_time, "📥 Downloading", filename or "File"
    ))

    try:
        file_path = await user.download_media(msg, file_name="downloads/", progress=download_cb)
    except Exception as e:
        progress_task.cancel()
        await smsg.edit(f"❌ Download error: {e}")
        return

    downloaded[0] = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    progress_task.cancel()

    if not file_path:
        await smsg.edit("❌ Download failed.")
        return

    await smsg.edit("📤 Uploading...")
    uploaded = [0]
    start_upload = time.time()

    async def upload_cb(current, total):
        uploaded[0] = current

    upload_task = asyncio.create_task(update_progress(
        smsg, lambda: uploaded[0], os.path.getsize(file_path), start_upload, "📤 Uploading", os.path.basename(file_path)
    ))

    try:
        send_func = {
            "Document": user.send_document,
            "Video": user.send_video,
            "Audio": user.send_audio,
            "Photo": user.send_photo,
            "Voice": user.send_voice,
            "Animation": user.send_animation,
            "Sticker": user.send_sticker,
        }.get(msg_type)

        if send_func:
            await send_func(DB_CHANNEL, file_path,
                            caption=msg.caption,
                            caption_entities=msg.caption_entities,
                            reply_markup=markup,
                            progress=upload_cb if msg_type != "Photo" else None)
        else:
            await smsg.edit("❌ Unsupported media type.")
            return
    except Exception as e:
        await smsg.edit(f"❌ Upload error: {e}")
    else:
        await smsg.delete()
        await asyncio.sleep(5)
    finally:
        upload_task.cancel()
        try:
            os.remove(file_path)
        except:
            pass

bot.run()
