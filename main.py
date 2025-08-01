import os, json, time, asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load config
with open('config.json', 'r') as f:
    CONFIG = json.load(f)

def getenv(key): return os.environ.get(key) or CONFIG.get(key)

API_ID = int(getenv("ID"))
API_HASH = getenv("HASH")
BOT_TOKEN = getenv("TOKEN")
STRING_SESSION = getenv("STRING")
DB_CHANNEL = int(getenv("DB_CHANNEL"))

ANIMATION_FRAMES = [".", "..", "..."]

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION) if STRING_SESSION else None

if user:
    user.start()

def humanbytes(size):
    power = 2**10
    n = 0
    units = ["B", "KiB", "MiB", "GiB"]
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
    current = float(current)
    total = float(total)
    percent = (current / total) * 100 if total else 0
    bar = "▪️" * int(percent // 10) + "▫️" * (10 - int(percent // 10))
    return bar, percent

async def update_progress(message, current_func, total, start, status, filename="File", anim=[0]):
    while True:
        current = current_func()
        bar, percent = progress_bar(current, total)
        elapsed = time.time() - start
        speed = current / elapsed if elapsed else 0
        eta = (total - current) / speed if speed else 0
        dots = ANIMATION_FRAMES[anim[0] % len(ANIMATION_FRAMES)]

        try:
            await message.edit_text(
                f"""{status} {dots}

📄 **{filename}**
[{bar}]
Progress: {percent:.2f}%
Size: {humanbytes(current)} of {humanbytes(total)}
Speed: {humanbytes(speed)}/s
ETA: {time_formatter(eta * 1000)}""")
        except: pass

        if current >= total: break
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
    await m.reply("👋 Send a Telegram post link (public or private), and I will upload its contents to your DB channel.")

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
                    msg = await (user if user else bot).get_messages(chat_id, msg_id)
                    await forward_message(m, msg)
                except Exception as e:
                    await m.reply(f"❌ Failed to fetch message {msg_id}: {e}")
        except Exception as e:
            await m.reply(f"❌ Error: {e}")

async def forward_message(m, msg):
    msg_type, filename, filesize = get_type(msg)
    text = msg.text or msg.caption or ""
    reply_markup = msg.reply_markup

    # Text-only or unsupported: forward with buttons
    if msg_type == "Text" or not msg_type or (not filename and not filesize):
        try:
            await user.send_message(DB_CHANNEL, text, entities=msg.entities or msg.caption_entities, reply_markup=reply_markup)
        except Exception as e:
            await m.reply(f"❌ Error forwarding text: {e}")
        return

    smsg = await m.reply("📥 Downloading...")
    downloaded = [0]
    start_time = time.time()

    async def download_cb(current, total): downloaded[0] = current

    progress_task = asyncio.create_task(update_progress(
        smsg, lambda: downloaded[0], filesize or 1, start_time, "📥 Downloading", filename or "File"
    ))

    file_path = await user.download_media(msg, file_name="downloads/", progress=download_cb)
    downloaded[0] = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    progress_task.cancel()

    if not file_path:
        await smsg.edit("❌ Download failed.")
        return

    await smsg.edit("📤 Uploading...")
    uploaded = [0]
    start_upload = time.time()

    async def upload_cb(current, total): uploaded[0] = current

    upload_task = asyncio.create_task(update_progress(
        smsg, lambda: uploaded[0], os.path.getsize(file_path), start_upload, "📤 Uploading", os.path.basename(file_path)
    ))

    try:
        kwargs = {
            "caption": text,
            "caption_entities": msg.caption_entities,
            "reply_markup": reply_markup,
            "progress": upload_cb
        }

        if msg_type == "Document":
            await user.send_document(DB_CHANNEL, file_path, **kwargs)
        elif msg_type == "Video":
            await user.send_video(DB_CHANNEL, file_path, **kwargs)
        elif msg_type == "Audio":
            await user.send_audio(DB_CHANNEL, file_path, **kwargs)
        elif msg_type == "Voice":
            await user.send_voice(DB_CHANNEL, file_path, **kwargs)
        elif msg_type == "Photo":
            kwargs.pop("progress")
            await user.send_photo(DB_CHANNEL, file_path, **kwargs)
        elif msg_type == "Animation":
            await user.send_animation(DB_CHANNEL, file_path, **kwargs)
        elif msg_type == "Sticker":
            await user.send_sticker(DB_CHANNEL, file_path)
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
        try: os.remove(file_path)
        except: pass

bot.run()
