from pyrogram import Client, filters
import asyncio
import os
import json
import time

# Load config
with open('config.json') as f:
    DATA = json.load(f)

def getenv(key):
    return os.environ.get(key) or DATA.get(key)

api_id = int(getenv("ID"))
api_hash = getenv("HASH")
bot_token = getenv("TOKEN")
DB_CHANNEL = int(getenv("DB_CHANNEL"))  # Make sure this is -100xxxxxxxxxx

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss) if ss else None
if acc:
    acc.start()

# Helpers
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

def time_formatter(ms):
    seconds = int(ms / 1000)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m" if h else f"{m}m {s}s" if m else f"{s}s"

def progress_bar(current, total):
    percent = current * 100 / total
    bar_len = 10
    filled = int(percent / (100 / bar_len))
    bar = '▪️' * filled + '▫️' * (bar_len - filled)
    return bar, percent

async def progress(current, total, message, start, status_type, anim_step):
    now = time.time()
    elapsed = now - start
    speed = current / elapsed if elapsed else 0
    eta = (total - current) / speed if speed else 0

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
    except:
        pass

    anim_step[0] += 1

async def update_progress_every_3s(message, total, start, status_type, current_func):
    anim_step = [0]
    while True:
        current = current_func()
        await progress(current, total, message, start, status_type, anim_step)
        if current >= total:
            break
        await asyncio.sleep(3)

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

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text("👋 Send me any Telegram post link (public/private).")

@bot.on_message(filters.text)
async def link_handler(client, message):
    text = message.text

    if ("https://t.me/+" in text) or ("joinchat/" in text):
        if acc:
            try:
                await acc.join_chat(text)
                await message.reply("✅ Joined.")
            except Exception as e:
                await message.reply(f"❌ Join error: {e}")
        return

    if "https://t.me/" not in text:
        await message.reply("⚠️ Please send a valid Telegram post link.")
        return

    parts = text.split("/")
    temp = parts[-1].replace("?single", "").split("-")

    try:
        from_id = int(temp[0].strip())
        to_id = int(temp[1].strip())
    except:
        from_id = to_id = int(temp[0].strip())

    for msgid in range(from_id, to_id + 1):
        if "https://t.me/c/" in text:
            chat_id = int("-100" + parts[4])
            if not acc:
                return await message.reply("❌ No user session (`acc`) found.")
            await handle_private(message, chat_id, msgid)
        else:
            username = parts[3]
            try:
                msg = await bot.get_messages(username, msgid)
            except:
                if not acc:
                    return await message.reply("❌ No user session (`acc`) found.")
                await handle_private(message, username, msgid)

        await asyncio.sleep(1)

async def handle_private(message, chat_id, msg_id):
    try:
        msg = await acc.get_messages(chat_id, msg_id)
    except Exception as e:
        return await message.reply(f"❌ Failed to fetch message: {e}")

    msg_type = get_message_type(msg)

    if msg_type == "Text":
        try:
            await acc.send_message(DB_CHANNEL, msg.text or "Empty", entities=msg.entities)
        except Exception as e:
            return await message.reply(f"❌ Failed to send message: {e}")
        return

    smsg = await message.reply("📥 Downloading...")
    start = time.time()
    current_downloaded = [0]

    async def dl_cb(current, total):
        current_downloaded[0] = current

    file = None
    progress_task = asyncio.create_task(update_progress_every_3s(smsg, msg.document.file_size if msg.document else msg.video.file_size if msg.video else 0, start, "📥 Downloading", lambda: current_downloaded[0]))
    
    try:
        file = await acc.download_media(msg, progress=dl_cb)
    except Exception as e:
        progress_task.cancel()
        return await smsg.edit(f"❌ Download failed: {e}")

    progress_task.cancel()

    if not file or not os.path.exists(file):
        return await smsg.edit("❌ File download failed.")

    current_uploaded = [0]

    async def ul_cb(current, total):
        current_uploaded[0] = current

    try:
        await smsg.edit("📤 Uploading...")
        upload_task = asyncio.create_task(update_progress_every_3s(smsg, os.path.getsize(file), time.time(), "📤 Uploading", lambda: current_uploaded[0]))

        sent = None
        if msg_type == "Document":
            sent = await acc.send_document(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities, progress=ul_cb)
        elif msg_type == "Video":
            sent = await acc.send_video(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, progress=ul_cb)
        elif msg_type == "Audio":
            sent = await acc.send_audio(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities, progress=ul_cb)
        elif msg_type == "Photo":
            sent = await acc.send_photo(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities)
        elif msg_type == "Voice":
            sent = await acc.send_voice(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities, progress=ul_cb)
        elif msg_type == "Animation":
            sent = await acc.send_animation(DB_CHANNEL, file)
        elif msg_type == "Sticker":
            sent = await acc.send_sticker(DB_CHANNEL, file)

    except Exception as e:
        await smsg.edit(f"❌ Upload failed: {e}")
    finally:
        upload_task.cancel()
        try:
            os.remove(file)
        except:
            pass
        await smsg.delete()

# Start bot
bot.run()
