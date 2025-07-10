
import pyrogram
from pyrogram import Client, filters
import time
import os
import threading
import json
from math import log, floor

with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")
bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss is not None:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None

DB_CHANNEL = -1001234567890  # Replace with your DB channel ID

def human_readable(size):
    if size == 0:
        return "0B"
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    i = int(floor(log(size, 1024)))
    p = pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {units[i]}"

def progress(current, total, message, type, start_time, filename=""):
    now = time.time()
    diff = now - start_time or 1
    percentage = current * 100 / total
    speed = current / diff
    eta = (total - current) / speed if speed > 0 else 0
    bar = '▪️' * int(10 * percentage // 100) + '▫️' * (10 - int(10 * percentage // 100))
    text = (
        f"**📄 File:** `{filename}`\n"
        f"📥 {'Downloading' if type == 'down' else 'Uploading'} ...\n"
        f"[{bar}]\n"
        f"Progress: `{percentage:.2f}%`\n"
        f"Size: `{human_readable(current)} of {human_readable(total)}`\n"
        f"Speed: `{human_readable(speed)}/s`\n"
        f"ETA: `{int(eta // 60)}m {int(eta % 60)}s`"
    )
    with open(f'{message.id}{type}status.txt', "w") as f:
        f.write(text)

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

def get_message_type(msg):
    if msg.document: return "Document"
    if msg.video: return "Video"
    if msg.animation: return "Animation"
    if msg.sticker: return "Sticker"
    if msg.voice: return "Voice"
    if msg.audio: return "Audio"
    if msg.photo: return "Photo"
    if msg.text: return "Text"

def handle_single_post(message, chat_username, msg_id):
    msg = acc.get_messages(chat_username, msg_id)
    msg_type = get_message_type(msg)

    if msg_type == "Text":
        acc.send_message(DB_CHANNEL, msg.text, entities=msg.entities)
        return True

    smsg = bot.send_message(message.chat.id, f"__Processing post {chat_username}/{msg_id}...__", reply_to_message_id=message.id)
    threading.Thread(target=lambda: status_updater(f'{message.id}downstatus.txt', smsg), daemon=True).start()

    start_time = time.time()
    filename = msg.file_name if hasattr(msg, 'file_name') and msg.file_name else "file"
    file = acc.download_media(msg, progress=progress, progress_args=[message, "down", start_time, filename])

    os.remove(f'{message.id}downstatus.txt')

    threading.Thread(target=lambda: status_updater(f'{message.id}upstatus.txt', smsg), daemon=True).start()

    try:
        kwargs = {'caption': msg.caption, 'caption_entities': msg.caption_entities} if msg.caption else {}
        if msg_type == "Document":
            acc.send_document(DB_CHANNEL, file, **kwargs)
        elif msg_type == "Video":
            acc.send_video(DB_CHANNEL, file, **kwargs)
        elif msg_type == "Photo":
            acc.send_photo(DB_CHANNEL, file, **kwargs)
        elif msg_type == "Audio":
            acc.send_audio(DB_CHANNEL, file, **kwargs)
        elif msg_type == "Voice":
            acc.send_voice(DB_CHANNEL, file, **kwargs)
        elif msg_type == "Sticker":
            acc.send_sticker(DB_CHANNEL, file)
        elif msg_type == "Animation":
            acc.send_animation(DB_CHANNEL, file)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Failed: {e}", reply_to_message_id=message.id)
        return False

    os.remove(file)
    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
    bot.delete_messages(message.chat.id, [smsg.id])
    return True

def batch_handler(message, links):
    success = 0
    fail = 0
    for link in links:
        try:
            parts = link.strip().split('/')
            chat_username = parts[-2]
            id_part = parts[-1]

            if '-' in id_part:
                start_id, end_id = map(int, id_part.split('-'))
                for mid in range(start_id, end_id + 1):
                    if handle_single_post(message, chat_username, mid):
                        success += 1
                    else:
                        fail += 1
            else:
                msg_id = int(id_part)
                if handle_single_post(message, chat_username, msg_id):
                    success += 1
                else:
                    fail += 1

        except Exception as e:
            fail += 1
            bot.send_message(message.chat.id, f"❗ Error: {e}\nLink: {link}", reply_to_message_id=message.id)

    bot.send_message(message.chat.id, f"✅ Batch Completed\n✔️ Success: {success}\n❌ Failed: {fail}", reply_to_message_id=message.id)

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Send `/save https://t.me/channel/10` for single post.\nSend `/save https://t.me/channel/10-15` for batch save to DB channel.", reply_to_message_id=message.id)

@bot.on_message(filters.command("save"))
async def save(client, message):
    if len(message.command) < 2:
        await message.reply_text("❗ Provide at least one link.")
        return
    links = message.command[1:]
    threading.Thread(target=batch_handler, args=(message, links), daemon=True).start()

bot.run()
