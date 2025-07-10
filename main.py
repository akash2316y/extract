import pyrogram
from pyrogram import Client, filters
import asyncio
import os
import json
import time

# Load configuration
with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")
DB_CHANNEL = int(getenv("DB_CHANNEL"))

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None

ANIMATION_FRAMES = [".", "..", "..."]

def humanbytes(size):
    if not size:
        return "0B"
    power = 2**10
    n = 0
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def time_formatter(milliseconds: int) -> str:
    seconds = int(milliseconds / 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h, {minutes}m"
    elif minutes:
        return f"{minutes}m, {seconds}s"
    else:
        return f"{seconds}s"

def progress_bar(current, total):
    percent = current * 100 / total if total else 0
    bar_length = 10
    filled_length = int(percent / (100 / bar_length))
    bar = '▪️' * filled_length + '▫️' * (bar_length - filled_length)
    return bar, percent

async def periodic_updater(message, status_type, start_time, total_size, current_func):
    anim_step = [0]
    while True:
        current = current_func()
        bar, percent = progress_bar(current, total_size)
        speed = current / (time.time() - start_time + 0.1)
        eta = (total_size - current) / speed if speed > 0 else 0
        dots = ANIMATION_FRAMES[anim_step[0] % len(ANIMATION_FRAMES)]

        text = f"""{status_type} {dots}

File: Unknown

[{bar}]
Progress: {percent:.2f}%
Size: {humanbytes(current)} of {humanbytes(total_size)}
Speed: {humanbytes(speed)}/s
ETA: {time_formatter(eta * 1000)}"""

        try:
            await message.edit_text(text)
        except:
            pass

        anim_step[0] += 1
        await asyncio.sleep(3)

@bot.on_message(filters.command(["start"]))
async def start_command(client, message):
    await message.reply_text(
        "👋 Hello!\n\nSend me any **Telegram post link** (public or private), and I'll try to **download and forward** the media to the saved channel.\n\n✅ Supported: Text, Files, Videos, Audios, Photos, Stickers.\n\nJust send the post link here!"
    )

@bot.on_message(filters.text)
async def main_handler(client, message):
    text = message.text

    if ("https://t.me/+" in text) or ("https://t.me/joinchat/" in text):
        if not acc:
            await message.reply_text("❌ This action requires account session (STRING missing).")
            return
        try:
            await acc.join_chat(text)
            await message.reply_text("✅ Successfully joined chat.")
        except:
            await message.reply_text("❌ Failed to join chat.")
        return

    if "https://t.me/" in text:
        parts = text.split("/")
        temp = parts[-1].replace("?single", "").split("-")

        try:
            from_id = int(temp[0].strip())
            to_id = int(temp[1].strip())
        except:
            from_id = to_id = int(temp[0].strip())

        for msgid in range(from_id, to_id + 1):
            if "https://t.me/c/" in text:
                chatid = int("-100" + parts[4])
                if not acc:
                    await message.reply_text("❌ Private content requires account session.")
                    return
                await handle_private(message, chatid, msgid)
            else:
                username = parts[3]
                try:
                    msg = await bot.get_messages(username, msgid)
                    await forward_message_to_channel(msg, message)
                except:
                    if not acc:
                        await message.reply_text("❌ Message not accessible.")
                        return
                    await handle_private(message, username, msgid)

            await asyncio.sleep(1)

async def handle_private(message, chatid, msgid):
    msg = await acc.get_messages(chatid, msgid)
    msg_type = get_message_type(msg)

    if msg_type == "Text":
        await acc.send_message(DB_CHANNEL, msg.text or "Empty", entities=msg.entities)
        return

    smsg = await message.reply_text("📥 Downloading...")

    start_time = time.time()
    progress_data = {"current": 0}

    async def update_progress(current, total):
        progress_data["current"] = current

    total_size = getattr(msg, msg_type.lower(), None).file_size if hasattr(msg, msg_type.lower()) else 0
    updater_task = asyncio.create_task(periodic_updater(smsg, "📥 Downloading", start_time, total_size, lambda: progress_data["current"]))

    file = await acc.download_media(msg, progress=update_progress)

    updater_task.cancel()

    if not file:
        await smsg.edit_text("❌ Download failed.")
        return

    start_upload = time.time()
    smsg = await message.reply_text("📤 Uploading...")

    progress_data_upload = {"current": 0}

    async def update_progress_upload(current, total):
        progress_data_upload["current"] = current

    total_upload_size = os.path.getsize(file)
    upload_task = asyncio.create_task(periodic_updater(smsg, "📤 Uploading", start_upload, total_upload_size, lambda: progress_data_upload["current"]))

    try:
        if msg_type == "Document":
            await acc.send_document(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities, progress=update_progress_upload)
        elif msg_type == "Video":
            await acc.send_video(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities, progress=update_progress_upload)
        elif msg_type == "Audio":
            await acc.send_audio(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities, progress=update_progress_upload)
        elif msg_type == "Photo":
            await acc.send_photo(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities)
        elif msg_type == "Voice":
            await acc.send_voice(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities, progress=update_progress_upload)
        elif msg_type == "Animation":
            await acc.send_animation(DB_CHANNEL, file)
        elif msg_type == "Sticker":
            await acc.send_sticker(DB_CHANNEL, file)
        await smsg.edit_text("✅ Uploaded successfully.")
    except Exception as e:
        await smsg.edit_text(f"❌ Upload failed: {e}")
    finally:
        upload_task.cancel()
        try:
            os.remove(file)
        except:
            pass

async def forward_message_to_channel(msg, message):
    try:
        await bot.copy_message(DB_CHANNEL, msg.chat.id, msg.id)
        await message.reply_text("✅ Message forwarded.")
    except:
        await message.reply_text("❌ Forwarding failed.")


def get_message_type(msg):
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
