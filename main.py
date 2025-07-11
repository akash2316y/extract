import os
import json
import time
import asyncio
from pyrogram import Client, filters

# Load config
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
    else:
        return f"{seconds}s"

def progress_bar(current, total):
    percent = current * 100 / total if total else 0
    filled = int(percent / 8.33)  # 12 bars
    bar = '▪️' * filled + '▫️' * (12 - filled)
    return bar, percent

async def progress(current, total, message, start, status, filename=None, anim_step=[0], last_update=[0]):
    now = time.time()
    if now - last_update[0] < 3 and current < total:
        return
    last_update[0] = now

    elapsed = now - start
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    bar, percent = progress_bar(current, total)
    dots = ANIMATION_FRAMES[anim_step[0] % len(ANIMATION_FRAMES)]
    anim_step[0] += 1

    text = f"""📄 <b>{filename or "Processing"}</b>\n
{status} {dots}

[{bar}]
<b>{percent:.2f}%</b> of <b>{humanbytes(total)}</b>
<b>Speed:</b> {humanbytes(speed)}/s
<b>ETA:</b> {time_formatter(eta * 1000)}"""

    try:
        await message.edit_text(text, parse_mode="html")
    except:
        pass

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("👋 Send me any Telegram post link to download and forward it with progress.")

@bot.on_message(filters.text)
async def text_handler(client, message):
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
            chatid = int("-100" + parts[4]) if "https://t.me/c/" in text else parts[3]
            await process_message(message, chatid, msgid)
            await asyncio.sleep(1)

async def process_message(message, chatid, msgid):
    try:
        msg = await acc.get_messages(chatid, msgid)
    except Exception as e:
        await message.reply_text(f"❌ Failed to fetch message:\n<code>{e}</code>")
        return

    msg_type = detect_type(msg)
    file_name = get_file_name(msg)
    smsg = await message.reply_text("📥 Downloading...")

    start_time = time.time()
    file_path = None

    try:
        file_path = await acc.download_media(
            msg,
            progress=progress,
            progress_args=[smsg, start_time, "📥 Downloading", file_name]
        )

        if not file_path:
            await smsg.edit_text("❌ Download failed.")
            return

        start_upload = time.time()
        await smsg.edit_text("📤 Uploading...")

        if msg_type == "Document":
            await acc.send_document(DB_CHANNEL, file_path, caption=msg.caption, caption_entities=msg.caption_entities,
                                    progress=progress, progress_args=[smsg, start_upload, "📤 Uploading", file_name])
        elif msg_type == "Video":
            await acc.send_video(DB_CHANNEL, file_path, caption=msg.caption, caption_entities=msg.caption_entities,
                                 duration=msg.video.duration, width=msg.video.width, height=msg.video.height,
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading", file_name])
        elif msg_type == "Audio":
            await acc.send_audio(DB_CHANNEL, file_path, caption=msg.caption, caption_entities=msg.caption_entities,
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading", file_name])
        elif msg_type == "Photo":
            await acc.send_photo(DB_CHANNEL, file_path, caption=msg.caption, caption_entities=msg.caption_entities)
        elif msg_type == "Voice":
            await acc.send_voice(DB_CHANNEL, file_path, caption=msg.caption, caption_entities=msg.caption_entities,
                                 progress=progress, progress_args=[smsg, start_upload, "📤 Uploading", file_name])
        elif msg_type == "Animation":
            await acc.send_animation(DB_CHANNEL, file_path)
        elif msg_type == "Sticker":
            await acc.send_sticker(DB_CHANNEL, file_path)

        await smsg.delete()  # ✅ Success: delete progress

    except Exception as e:
        await smsg.edit_text(f"❌ Error:\n<code>{e}</code>")
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

def detect_type(msg):
    if msg.document: return "Document"
    if msg.video: return "Video"
    if msg.audio: return "Audio"
    if msg.photo: return "Photo"
    if msg.voice: return "Voice"
    if msg.animation: return "Animation"
    if msg.sticker: return "Sticker"
    return "Text"

def get_file_name(msg):
    if msg.document: return msg.document.file_name
    if msg.video: return msg.video.file_name
    if msg.audio: return msg.audio.file_name
    if msg.animation: return msg.animation.file_name
    if msg.photo: return "Photo.jpg"
    if msg.voice: return "Voice.ogg"
    if msg.sticker: return "Sticker.webp"
    return None

bot.run()
