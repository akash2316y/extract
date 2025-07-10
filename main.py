import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired
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

async def progress(current, total, message, start, status_type, anim_step=[0]):
    now = time.time()
    elapsed = now - start
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    bar, percent = progress_bar(current, total)
    dots = ANIMATION_FRAMES[anim_step[0] % len(ANIMATION_FRAMES)]

    filename = message.caption if message.caption else "File"

    text = f"""{status_type} {dots}

File: {filename}

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

@bot.on_message(filters.command(["start"]))
async def start_command(client, message):
    await message.reply_text(
        "👋 Hello!\n\nSend me any **public or private Telegram post link** (message link), and I will try to **download the media and forward it** to the saved channel.\n\n✅ Supported: Text, Files, Videos, Audios, Photos, Stickers.\n\nJust send the post link here!"
    )

@bot.on_message(filters.text)
async def main_handler(client, message):
    text = message.text

    if ("https://t.me/+" in text) or ("https://t.me/joinchat/" in text):
        if not acc:
            await message.reply_text("❌ This action requires an account session. Please set STRING in config.")
            return
        try:
            await acc.join_chat(text)
            await message.reply_text("✅ Successfully joined the group/channel.")
        except:
            await message.reply_text("❌ Failed to join chat. The link might be invalid or expired.")
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
                    await message.reply_text("❌ Private groups require account session. Please set STRING.")
                    return
                await handle_private(message, chatid, msgid)
            else:
                username = parts[3]
                try:
                    msg = await bot.get_messages(username, msgid)
                    await forward_message_to_channel(msg, message)
                except:
                    if not acc:
                        await message.reply_text("❌ Unable to fetch message. It might be private or inaccessible.")
                        return
                    await handle_private(message, username, msgid)

            await asyncio.sleep(1)

async def handle_private(message, chatid, msgid):
    msg = await acc.get_messages(chatid, msgid)
    msg_type = get_message_type(msg)

    if msg_type == "Text":
        await acc.send_message(DB_CHANNEL, msg.text or "Empty Message", entities=msg.entities)
        return

    smsg = await message.reply_text("📥 Downloading...")

    start_time = time.time()
    file = await acc.download_media(msg, progress=progress, progress_args=[smsg, start_time, "📥 Downloading"])

    if not file:
        await smsg.edit_text("❌ Failed to download.")
        return

    start_upload = time.time()
    await smsg.edit_text("📤 Uploading...")

    try:
        sent_msg = None

        if msg_type == "Document":
            sent_msg = await acc.send_document(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities,
                                               progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Video":
            sent_msg = await acc.send_video(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities,
                                            duration=msg.video.duration, width=msg.video.width, height=msg.video.height,
                                            progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Audio":
            sent_msg = await acc.send_audio(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities,
                                            progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Photo":
            sent_msg = await acc.send_photo(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities)
        elif msg_type == "Voice":
            sent_msg = await acc.send_voice(DB_CHANNEL, file, caption=msg.caption or os.path.basename(file), caption_entities=msg.caption_entities,
                                            progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Animation":
            sent_msg = await acc.send_animation(DB_CHANNEL, file)
        elif msg_type == "Sticker":
            sent_msg = await acc.send_sticker(DB_CHANNEL, file)

    except Exception as e:
        await smsg.edit_text(f"❌ Upload failed: {e}")
    finally:
        try:
            os.remove(file)
        except:
            pass
        await smsg.delete()

async def forward_message_to_channel(msg, message):
    try:
        await bot.copy_message(DB_CHANNEL, msg.chat.id, msg.id)
        await message.reply_text("✅ Message forwarded successfully.")
    except:
        await message.reply_text("❌ Failed to forward message.")


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
