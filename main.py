import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
import asyncio
import os
import json
import time
import math

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
    percent = current * 100 / total
    bar_length = 10
    filled_length = int(percent / (100 / bar_length))
    bar = '▪️' * filled_length + '▫️' * (bar_length - filled_length)
    return bar, percent

async def progress(current, total, message, start, status_type, anim_step=[0], last_edit_time=[0]):
    now = time.time()
    elapsed = now - start
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    if now - last_edit_time[0] < 3 and current != total:
        return

    bar, percent = progress_bar(current, total)
    dots = ANIMATION_FRAMES[anim_step[0] % len(ANIMATION_FRAMES)]

    text = f"""{status_type} {dots}

[{bar}]
Progress: {percent:.2f}%
Size: {humanbytes(current)} of {humanbytes(total)}
Speed: {humanbytes(speed)}/s
ETA: {time_formatter(eta * 1000)}"""

    try:
        await message.edit_text(text)
        last_edit_time[0] = now
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception:
        pass

    anim_step[0] += 1

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

@bot.on_message(filters.command(["start"]))
async def start_command(client, message):
    await message.reply_text("👋 Hi! Send me any Telegram post link, and I'll try to download and forward it.\n\nTo restart: Restarting...")

@bot.on_message(filters.text | filters.media)
async def main_handler(client, message):
    text = message.text or ""

    if not text and not message.media:
        return

    if ("https://t.me/+" in text) or ("https://t.me/joinchat/" in text):
        if not acc:
            return
        try:
            await acc.join_chat(text)
        except Exception as e:
            await message.reply_text(f"❌ Failed to join chat:\n`{e}`")
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
                    return
                await handle_private(message, chatid, msgid)
            else:
                username = parts[3]
                try:
                    msg = await bot.get_messages(username, msgid)
                except:
                    if not acc:
                        return
                    await handle_private(message, username, msgid)

            await asyncio.sleep(1)

async def handle_private(message, chatid, msgid):
    try:
        msg = await acc.get_messages(chatid, msgid)
    except Exception as e:
        await message.reply_text(f"❌ Message fetch failed:\n`{e}`")
        return

    if not msg:
        await message.reply_text("❌ No message found.")
        return

    msg_type = get_message_type(msg)

    if msg_type == "Text":
        await acc.send_message(DB_CHANNEL, msg.text or "Empty Message", entities=msg.entities)
        return

    if not msg.media:
        await message.reply_text("❌ This message has no downloadable media.")
        return

    smsg = await message.reply_text("📥 Downloading...")

    start_time = time.time()
    try:
        file = await acc.download_media(msg, progress=progress, progress_args=[smsg, start_time, "📥 Downloading"])
    except Exception as e:
        await smsg.edit_text(f"❌ Download failed:\n`{e}`")
        return

    if not file:
        await smsg.edit_text("❌ Failed to download media.")
        return

    start_upload = time.time()
    await smsg.edit_text("📤 Uploading...")

    try:
        if msg_type == "Document":
            await acc.send_document(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                    progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Video":
            await acc.send_video(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 duration=getattr(msg.video, 'duration', None),
                                 width=getattr(msg.video, 'width', None),
                                 height=getattr(msg.video, 'height', None),
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Audio":
            await acc.send_audio(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Photo":
            await acc.send_photo(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities)
        elif msg_type == "Voice":
            await acc.send_voice(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Animation":
            await acc.send_animation(DB_CHANNEL, file)
        elif msg_type == "Sticker":
            await acc.send_sticker(DB_CHANNEL, file)
        else:
            await smsg.edit_text("❌ Unsupported media type.")
            return
    except Exception as e:
        await smsg.edit_text(f"❌ Upload failed:\n`{e}`")
    finally:
        try:
            os.remove(file)
        except:
            pass
        await smsg.delete()

bot.run()
