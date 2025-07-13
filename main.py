import os
import json
import time
import asyncio
from pyrogram import Client, filters

# Load configuration
with open("config.json") as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var)

api_id = int(getenv("ID"))
api_hash = getenv("HASH")
bot_token = getenv("TOKEN")
db_channel = int(getenv("DB_CHANNEL"))
session_string = getenv("STRING")

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
user = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=session_string)

ANIMATION_FRAMES = [".", "..", "..."]

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
    if hours:
        return f"{hours}h {minutes}m"
    elif minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

def progress_bar(current, total):
    percent = current * 100 / total
    filled = int(percent / 10)
    return "▪️" * filled + "▫️" * (10 - filled), percent

async def show_progress(current, total, message, start, status, anim_step):
    now = time.time()
    elapsed = now - start
    speed = current / elapsed if elapsed else 0
    eta = (total - current) / speed if speed else 0
    bar, percent = progress_bar(current, total)
    dots = ANIMATION_FRAMES[anim_step[0] % len(ANIMATION_FRAMES)]

    text = f"""{status} {dots}
[{bar}]
Progress: {percent:.2f}%
Size: {humanbytes(current)} of {humanbytes(total)}
Speed: {humanbytes(speed)}/s
ETA: {time_formatter(eta * 1000)}"""
    try:
        await message.edit_text(text)
    except:
        pass
    anim_step[0] += 1

async def update_progress_loop(message, total, start, status, get_current):
    anim_step = [0]
    while True:
        current = get_current()
        await show_progress(current, total, message, start, status, anim_step)
        if current >= total:
            break
        await asyncio.sleep(3)

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply("Send me a Telegram post link (even from private channels).")

@bot.on_message(filters.text)
async def link_handler(client, message):
    link = message.text.strip()

    try:
        await user.start()
    except:
        await message.reply("Failed to start user session.")
        return

    if "t.me/+" in link or "joinchat" in link:
        try:
            await user.join_chat(link)
            await message.reply("✅ Joined private channel.")
        except Exception as e:
            await message.reply(f"❌ Failed to join: {e}")
        return

    try:
        if "t.me/c/" in link:
            parts = link.split("/")
            msg_id = int(parts[-1])
            chat_id = int("-100" + parts[-2])
        else:
            parts = link.split("/")
            username = parts[3]
            msg_id = int(parts[-1].split("-")[0])
            chat = await user.get_chat(username)
            chat_id = chat.id

        msg = await user.get_messages(chat_id, msg_id)

        msg_type = get_type(msg)
        smsg = await message.reply("📥 Downloading...")

        start_time = time.time()
        current_downloaded = [0]

        async def on_download(current, total):
            current_downloaded[0] = current

        progress_task = asyncio.create_task(update_progress_loop(smsg, msg.video.file_size if msg.video else msg.document.file_size if msg.document else 0, start_time, "📥 Downloading", lambda: current_downloaded[0]))

        file_path = await user.download_media(msg, progress=on_download)
        progress_task.cancel()

        if not file_path:
            await smsg.edit("❌ Failed to download.")
            return

        await smsg.edit("📤 Uploading...")
        start_upload = time.time()
        current_uploaded = [0]

        async def on_upload(current, total):
            current_uploaded[0] = current

        progress_task2 = asyncio.create_task(update_progress_loop(smsg, os.path.getsize(file_path), start_upload, "📤 Uploading", lambda: current_uploaded[0]))

        if msg_type == "Document":
            await user.send_document(db_channel, file_path, caption=msg.caption, caption_entities=msg.caption_entities, progress=on_upload)
        elif msg_type == "Video":
            await user.send_video(db_channel, file_path, caption=msg.caption, caption_entities=msg.caption_entities, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, progress=on_upload)
        elif msg_type == "Photo":
            await user.send_photo(db_channel, file_path, caption=msg.caption, caption_entities=msg.caption_entities)
        else:
            await user.send_document(db_channel, file_path, caption=msg.caption, caption_entities=msg.caption_entities, progress=on_upload)

        progress_task2.cancel()
        await smsg.delete()

        try:
            os.remove(file_path)
        except:
            pass

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

def get_type(msg):
    if msg.document: return "Document"
    if msg.video: return "Video"
    if msg.audio: return "Audio"
    if msg.photo: return "Photo"
    if msg.voice: return "Voice"
    if msg.animation: return "Animation"
    if msg.sticker: return "Sticker"
    if msg.text: return "Text"
    return None

bot.run()
