import os
import time
import json
import threading
from math import log, floor

from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied


# Load configuration from file or environment variables
with open('config.json', 'r') as f:
    DATA = json.load(f)


def getenv(var):
    return os.environ.get(var) or DATA.get(var, None)


bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Optional User Account
ss = getenv("STRING")
if ss:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None


# Human readable size
def human_readable(size):
    if size == 0:
        return "0B"
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    i = int(floor(log(size, 1024)))
    p = pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {units[i]}"


# Progress writer
def progress(current, total, message, type, start_time, filename=""):
    now = time.time()
    diff = now - start_time
    if diff == 0:
        diff = 1

    percentage = current * 100 / total
    speed = current / diff
    eta = (total - current) / speed if speed > 0 else 0

    bar_length = 10
    filled_length = int(bar_length * percentage // 100)
    bar = '▪️' * filled_length + '▫️' * (bar_length - filled_length)

    current_human = human_readable(current)
    total_human = human_readable(total)
    speed_human = human_readable(speed) + "/s"

    eta_minutes = int(eta // 60)
    eta_seconds = int(eta % 60)
    eta_formatted = f"{eta_minutes}m, {eta_seconds}s"

    text = (
        f"**📄 File:** `{filename}`\n"
        f"📥 {'Downloading' if type == 'down' else 'Uploading'} ...\n"
        f"[{bar}]\n"
        f"Progress: `{percentage:.2f}%`\n"
        f"Size: `{current_human} of {total_human}`\n"
        f"Speed: `{speed_human}`\n"
        f"ETA: `{eta_formatted}`"
    )

    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(text)


# Unified status updater
def status_updater(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(2)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, txt)
            time.sleep(5)
        except:
            time.sleep(3)


# Get message type
def get_message_type(msg):
    if msg.document: return "Document"
    if msg.video: return "Video"
    if msg.animation: return "Animation"
    if msg.sticker: return "Sticker"
    if msg.voice: return "Voice"
    if msg.audio: return "Audio"
    if msg.photo: return "Photo"
    if msg.text: return "Text"
    return None


# Handle private message (Download + Upload)
def handle_private(message, chatid, msgid):
    msg = acc.get_messages(chatid, msgid)
    msg_type = get_message_type(msg)

    if msg_type == "Text":
        bot.send_message(
            message.chat.id,
            msg.text,
            entities=msg.entities,
            reply_to_message_id=message.id
        )
        return

    smsg = bot.send_message(message.chat.id, '__Downloading__', reply_to_message_id=message.id)

    # Start download status thread
    dosta = threading.Thread(target=lambda: status_updater(f'{message.id}downstatus.txt', smsg), daemon=True)
    dosta.start()

    start_time = time.time()
    filename = getattr(msg, 'file_name', "file")

    file = acc.download_media(msg, progress=progress, progress_args=[message, "down", start_time, filename])

    os.remove(f'{message.id}downstatus.txt')

    # Start upload status thread
    upsta = threading.Thread(target=lambda: status_updater(f'{message.id}upstatus.txt', smsg), daemon=True)
    upsta.start()

    try:
        start_time_up = time.time()
        send_args = dict(
            chat_id=message.chat.id,
            file_name=os.path.basename(file),
            caption=msg.caption,
            caption_entities=msg.caption_entities,
            reply_to_message_id=message.id,
            progress=progress,
            progress_args=[message, "up", start_time_up, os.path.basename(file)],
            stream=True
        )

        if msg_type == "Document":
            acc.send_document(file=file, **send_args)
        elif msg_type == "Video":
            acc.send_video(file=file, **send_args)
        elif msg_type == "Photo":
            acc.send_photo(file=file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id)
        elif msg_type == "Audio":
            acc.send_audio(file=file, **send_args)
        elif msg_type == "Voice":
            acc.send_voice(file=file, **send_args)
        elif msg_type == "Sticker":
            acc.send_sticker(file=file, reply_to_message_id=message.id)
        elif msg_type == "Animation":
            acc.send_animation(file=file, reply_to_message_id=message.id, stream=True)

    except Exception as e:
        bot.send_message(message.chat.id, f"__Upload failed__: {e}", reply_to_message_id=message.id)

    os.remove(file)
    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')

    bot.delete_messages(message.chat.id, [smsg.id])


# Start command
@bot.on_message(filters.command("start"))
async def start(client, message):
    await bot.send_message(message.chat.id, "Hi! Send me a Telegram post link to download and upload with progress.", reply_to_message_id=message.id)


bot.run()
