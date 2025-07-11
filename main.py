import os
import json
import time
import math
import asyncio
from pyrogram import Client, filters

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
acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss) if ss else None
if acc:
    acc.start()

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
        return f"{hours}h {minutes}m"
    elif minutes:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def progress_bar(current, total):
    percent = current * 100 / total if total else 0
    bar_length = 12
    filled_length = int(percent / (100 / bar_length))
    bar = '▪️' * filled_length + '▫️' * (bar_length - filled_length)
    return bar, percent

async def progress(current, total, message, start, status_type, filename=None, anim_step=[0], last_update=[0]):
    now = time.time()
    elapsed = now - start
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    bar, percent = progress_bar(current, total)
    dots = ANIMATION_FRAMES[anim_step[0] % len(ANIMATION_FRAMES)]

    # Only update every 3 seconds or when complete
    if now - last_update[0] < 3 and current < total:
        return
    last_update[0] = now

    text = f"""📄 <b>{filename or "Processing..."}</b>\n
{status_type} {dots}

[{bar}]
Progress: <b>{percent:.2f}%</b>
Size: <b>{humanbytes(current)}</b> of <b>{humanbytes(total)}</b>
Speed: <b>{humanbytes(speed)}/s</b>
ETA: <b>{time_formatter(eta * 1000)}</b>"""

    try:
        await message.edit_text(text, parse_mode="html")
    except:
        pass

    anim_step[0] += 1

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("👋 Hi! Send me any Telegram post link, and I'll try to download and forward it with progress.")

@bot.on_message(filters.text)
async def main_handler(client, message):
    text = message.text

    if ("https://t.me/+" in text) or ("https://t.me/joinchat/" in text):
        if not acc:
            return
        try:
            await acc.join_chat(text)
        except:
            pass
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
        await message.reply_text(f"❌ Failed to fetch message: {e}")
        return

    msg_type = get_message_type(msg)
    file_name = None

    if msg_type == "Text":
        await acc.send_message(DB_CHANNEL, msg.text or "Empty Message", entities=msg.entities)
        return

    smsg = await message.reply_text(f"📥 Downloading...")

    start_time = time.time()
    file = None
    try:
        if msg.document:
            file_name = msg.document.file_name
        elif msg.video:
            file_name = msg.video.file_name
        elif msg.audio:
            file_name = msg.audio.file_name
        elif msg.photo:
            file_name = "Photo.jpg"
        elif msg.voice:
            file_name = "Voice.ogg"
        elif msg.animation:
            file_name = msg.animation.file_name
        elif msg.sticker:
            file_name = "Sticker.webp"

        file = await acc.download_media(
            msg,
            progress=progress,
            progress_args=[smsg, start_time, "📥 Downloading", file_name]
        )

        if not file:
            await smsg.edit_text("❌ Failed to download.")
            return

        start_upload = time.time()
        await smsg.edit_text("📤 Uploading...")

        if msg_type == "Document":
            await acc.send_document(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                    progress=progress, progress_args=[smsg, start_upload, "📤 Uploading", file_name])
        elif msg_type == "Video":
            await acc.send_video(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 duration=msg.video.duration, width=msg.video.width, height=msg.video.height,
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading", file_name])
        elif msg_type == "Audio":
            await acc.send_audio(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading", file_name])
        elif msg_type == "Photo":
            await acc.send_photo(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities)
        elif msg_type == "Voice":
            await acc.send_voice(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading", file_name])
        elif msg_type == "Animation":
            await acc.send_animation(DB_CHANNEL, file)
        elif msg_type == "Sticker":
            await acc.send_sticker(DB_CHANNEL, file)

    except Exception as e:
        await smsg.edit_text(f"❌ Upload failed: {e}")
    finally:
        if file:
            try:
                os.remove(file)
            except:
                pass
        await smsg.delete()

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


