import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
import asyncio
import os
import json
import sys
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
STATE_FILE = "state.json"

# Utility functions

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
        return f"{hours}h, {minutes}m, {seconds}s"
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

# State handling

def save_state(chatid, msgid):
    with open(STATE_FILE, 'w') as f:
        json.dump({"chatid": chatid, "msgid": msgid}, f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return None

def clear_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def restart_bot():
    print("🔄 Restarting bot...")
    os.execv(sys.executable, ['python'] + sys.argv)

async def safe_edit(message, text):
    try:
        await message.edit_text(text)
    except FloodWait as e:
        wait_time = time_formatter(e.value * 1000)
        await message.edit_text(f"⏳ FloodWait: Sleeping for {wait_time}")
        print(f"FloodWait: {e.value} seconds")
        await asyncio.sleep(e.value)
        restart_bot()
    except Exception as e:
        print(f"Edit failed: {e}")

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

    await safe_edit(message, text)

    last_edit_time[0] = now
    anim_step[0] += 1

# Command handlers

@bot.on_message(filters.command(["start"]))
async def start_command(client, message):
    state = load_state()
    if state:
        await message.reply_text(f"🔄 Resuming last task: Chat `{state['chatid']}`, Msg `{state['msgid']}`")
        await handle_private(message, state['chatid'], state['msgid'])
        clear_state()
    else:
        await message.reply_text("👋 Hi! Send me any Telegram post link, and I'll try to download and forward it.")

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
            try:
                if "https://t.me/c/" in text:
                    chatid = int("-100" + parts[4])
                    save_state(chatid, msgid)
                    await handle_private(message, chatid, msgid)
                else:
                    username = parts[3]
                    save_state(username, msgid)
                    try:
                        msg = await bot.get_messages(username, msgid)
                    except:
                        if not acc:
                            return
                        await handle_private(message, username, msgid)

                await asyncio.sleep(1)

            except FloodWait as e:
                wait_time = time_formatter(e.value * 1000)
                await message.reply_text(f"⏳ FloodWait: Sleeping for {wait_time}")
                print(f"FloodWait: {e.value} seconds")
                await asyncio.sleep(e.value)
                restart_bot()
            except Exception as e:
                print(f"Error: {e}")
        clear_state()

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
        await safe_edit(smsg, "❌ Failed to download.")
        return

    start_upload = time.time()
    await safe_edit(smsg, "📤 Uploading...")

    try:
        if msg_type == "Document":
            await acc.send_document(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                     progress=progress, progress_args=[smsg, start_upload, "📤 Uploading"])
        elif msg_type == "Video":
            await acc.send_video(DB_CHANNEL, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                  duration=msg.video.duration, width=msg.video.width, height=msg.video.height,
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

    except FloodWait as e:
        wait_time = time_formatter(e.value * 1000)
        await message.reply_text(f"⏳ FloodWait during upload: Sleeping for {wait_time}")
        print(f"FloodWait during upload: {e.value} seconds")
        await asyncio.sleep(e.value)
        restart_bot()
    except Exception as e:
        await safe_edit(smsg, f"❌ Upload failed: {e}")
    finally:
        try:
            os.remove(file)
        except:
            pass
        await smsg.delete()

# Message type detection

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

