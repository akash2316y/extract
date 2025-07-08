import os
import json
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired

# Load configuration
with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = int(getenv("ID"))
string_session = getenv("STRING")

# Multiple DB channels
DB_CHANNELS = [int(x.strip()) for x in getenv("DB_CHANNELS").split(",")]

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=string_session) if string_session else None
if acc:
    acc.start()

# Human-readable file size
def humanbytes(size):
    if not size:
        return "0B"
    power = 2 ** 10
    n = 0
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

# Time formatter
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

# Progress bar
def progress_bar(current, total):
    percent = current * 100 / total
    bar_length = 10
    filled_length = int(percent / (100 / bar_length))
    bar = '▪️' * filled_length + '▫️' * (bar_length - filled_length)
    return bar, percent

async def progress(current, total, message, start, status_type):
    now = time.time()
    elapsed = now - start
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    bar, percent = progress_bar(current, total)
    text = f"""📥 {status_type}ing

[{bar}]
Progress: {percent:.2f}%
Size: {humanbytes(current)} of {humanbytes(total)}
Speed: {humanbytes(speed)}/s
ETA: {time_formatter(eta * 1000)}"""

    try:
        await message.edit_text(text)
    except:
        pass

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
async def start_command(client, message):
    await message.reply_text("👋 Hi! Send me any Telegram post link, and I'll download and forward it to channels.")

@bot.on_message(filters.text)
async def main_handler(client, message):
    text = message.text

    if ("https://t.me/+" in text) or ("https://t.me/joinchat/" in text):
        if not acc:
            await message.reply_text("❌ String session not set.")
            return
        try:
            await acc.join_chat(text)
            await message.reply_text("✅ Chat joined.")
        except UserAlreadyParticipant:
            await message.reply_text("✅ Already in chat.")
        except InviteHashExpired:
            await message.reply_text("❌ Invalid invite link.")
        except Exception as e:
            await message.reply_text(f"❌ Error: {e}")
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
                    await message.reply_text("❌ String session not set.")
                    return
                await handle_private(chatid, msgid)
            else:
                username = parts[3]
                try:
                    msg = await bot.get_messages(username, msgid)
                    await forward_to_channels(msg)
                except:
                    if not acc:
                        await message.reply_text("❌ String session not set.")
                        return
                    await handle_private(username, msgid)

            await asyncio.sleep(1)

async def handle_private(chatid, msgid):
    msg = await acc.get_messages(chatid, msgid)
    await forward_to_channels(msg)

async def forward_to_channels(msg):
    msg_type = get_message_type(msg)

    # For pure text, send as-is to all channels
    if msg_type == "Text":
        for channel in DB_CHANNELS:
            await bot.send_message(channel, msg.text or "Empty Message")
        return

    # For media files
    smsg = await bot.send_message(DB_CHANNELS[0], "📥 Downloading...")
    start_time = time.time()

    try:
        file = await acc.download_media(msg, progress=progress, progress_args=[smsg, start_time, "Download"])
    except:
        await smsg.edit_text("❌ Download failed.")
        return

    if not file:
        await smsg.edit_text("❌ File missing.")
        return

    upload_time = time.time()
    await smsg.edit_text("📤 Uploading...")

    for channel in DB_CHANNELS:
        try:
            if msg_type == "Document":
                await acc.send_document(channel, file, caption=msg.caption, caption_entities=msg.caption_entities, progress=progress, progress_args=[smsg, upload_time, "Upload"])
            elif msg_type == "Video":
                await acc.send_video(channel, file, caption=msg.caption, caption_entities=msg.caption_entities, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, progress=progress, progress_args=[smsg, upload_time, "Upload"])
            elif msg_type == "Audio":
                await acc.send_audio(channel, file, caption=msg.caption, caption_entities=msg.caption_entities, progress=progress, progress_args=[smsg, upload_time, "Upload"])
            elif msg_type == "Photo":
                await acc.send_photo(channel, file, caption=msg.caption, caption_entities=msg.caption_entities)
            elif msg_type == "Voice":
                await acc.send_voice(channel, file, caption=msg.caption, caption_entities=msg.caption_entities, progress=progress, progress_args=[smsg, upload_time, "Upload"])
            elif msg_type == "Animation":
                await acc.send_animation(channel, file)
            elif msg_type == "Sticker":
                await acc.send_sticker(channel, file)
        except Exception as e:
            await bot.send_message(channel, f"❌ Upload failed: {e}")

    try:
        os.remove(file)
    except:
        pass

    await smsg.delete()

bot.run()
