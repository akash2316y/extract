import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import time
import os
import threading
import json
import asyncio

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

progress_start_time = {}

# Helper functions

def human_readable(size):
    if size == 0:
        return "0B"
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size >= power and n < 4:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"


def get_progress_bar(current, total):
    percent = current / total
    bar_length = 10
    filled_length = int(bar_length * percent)
    bar = '▪️' * filled_length + '▫️' * (bar_length - filled_length)
    return bar


def progress(current, total, message, type):
    now = time.time()
    key = f"{message.id}{type}"

    if key not in progress_start_time:
        progress_start_time[key] = now
        start_time = now
    else:
        start_time = progress_start_time[key]

    elapsed_time = now - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    percentage = current * 100 / total
    bar = get_progress_bar(current, total)

    eta_str = time.strftime("%M:%S", time.gmtime(eta))
    speed_str = human_readable(speed) + "/s"
    current_str = human_readable(current)
    total_str = human_readable(total)

    status_text = (
        f"📥 {'Downloading' if type == 'down' else 'Uploading'}\n\n"
        f"[{bar}]\n"
        f"Progress: {percentage:.2f}%\n"
        f"Size: {current_str} of {total_str}\n"
        f"Speed: {speed_str}\n"
        f"ETA: {eta_str}"
    )

    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(status_text)


# Status updaters

def downstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)

    time.sleep(3)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, txt)
            time.sleep(10)
        except:
            time.sleep(5)


def upstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)

    time.sleep(3)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, txt)
            time.sleep(10)
        except:
            time.sleep(5)


# Get message type

def get_message_type(msg):
    try:
        msg.document.file_id
        return "Document"
    except:
        pass
    try:
        msg.video.file_id
        return "Video"
    except:
        pass
    try:
        msg.animation.file_id
        return "Animation"
    except:
        pass
    try:
        msg.sticker.file_id
        return "Sticker"
    except:
        pass
    try:
        msg.voice.file_id
        return "Voice"
    except:
        pass
    try:
        msg.audio.file_id
        return "Audio"
    except:
        pass
    try:
        msg.photo.file_id
        return "Photo"
    except:
        pass
    try:
        msg.text
        return "Text"
    except:
        pass


# Start command

@bot.on_message(filters.command(["start"]))
async def send_start(client, message):
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"👋 Hi **{message.from_user.mention}**, I can send you restricted content by its post link.\n\n{USAGE}",
        reply_to_message_id=message.id
    )


@bot.on_message(filters.text)
async def save(client, message):
    print(message.text)

    if "https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text:
        if acc is None:
            await bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
            return

        try:
            await acc.join_chat(message.text)
            await bot.send_message(message.chat.id, "**Chat Joined**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            await bot.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            await bot.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)
        except Exception as e:
            await bot.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)
        return

    elif "https://t.me/" in message.text:
        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())
        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID

        for msgid in range(fromID, toID + 1):
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])
                if acc is None:
                    await bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                    return
                await handle_private(message, chatid, msgid)

            elif "https://t.me/b/" in message.text:
                username = datas[4]
                if acc is None:
                    await bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                    return
                await handle_private(message, username, msgid)

            else:
                username = datas[3]
                try:
                    msg = await bot.get_messages(username, msgid)
                except UsernameNotOccupied:
                    await bot.send_message(message.chat.id, "**The username is not occupied by anyone**", reply_to_message_id=message.id)
                    return
                try:
                    if '?single' not in message.text:
                        await bot.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    else:
                        await bot.copy_media_group(message.chat.id, msg.chat.id, [msg.id], reply_to_message_id=message.id)
                except:
                    if acc is None:
                        await bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                        return
                    await handle_private(message, username, msgid)

            await asyncio.sleep(3)


async def handle_private(message, chatid, msgid):
    msg = await acc.get_messages(chatid, msgid)
    msg_type = get_message_type(msg)

    if msg_type == "Text":
        await bot.send_message(message.chat.id, msg.text, entities=msg.entities, reply_to_message_id=message.id)
        return

    smsg = await bot.send_message(message.chat.id, '__Downloading__', reply_to_message_id=message.id)

    asyncio.create_task(asyncio.to_thread(downstatus, f'{message.id}downstatus.txt', smsg))

    file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])

    if os.path.exists(f'{message.id}downstatus.txt'):
        os.remove(f'{message.id}downstatus.txt')
        progress_start_time.pop(f"{message.id}down", None)

    asyncio.create_task(asyncio.to_thread(upstatus, f'{message.id}upstatus.txt', smsg))

    thumb = None

    try:
        if msg_type == "Document":
            try:
                thumb = await acc.download_media(msg.document.thumbs[0].file_id)
            except:
                thumb = None

            await acc.send_document(
                message.chat.id, file, thumb=thumb, caption=msg.caption,
                caption_entities=msg.caption_entities, reply_to_message_id=message.id,
                progress=progress, progress_args=[message, "up"]
            )

        elif msg_type == "Video":
            try:
                thumb = await acc.download_media(msg.video.thumbs[0].file_id)
            except:
                thumb = None

            await bot.send_video(
                message.chat.id, file, duration=msg.video.duration, width=msg.video.width,
                height=msg.video.height, thumb=thumb, caption=msg.caption,
                caption_entities=msg.caption_entities, reply_to_message_id=message.id,
                progress=progress, progress_args=[message, "up"]
            )

        elif msg_type == "Animation":
            await bot.send_animation(message.chat.id, file, reply_to_message_id=message.id)

        elif msg_type == "Sticker":
            await bot.send_sticker(message.chat.id, file, reply_to_message_id=message.id)

        elif msg_type == "Voice":
            await bot.send_voice(
                message.chat.id, file, caption=msg.caption,
                caption_entities=msg.caption_entities, reply_to_message_id=message.id,
                progress=progress, progress_args=[message, "up"]
            )

        elif msg_type == "Audio":
            try:
                thumb = await acc.download_media(msg.audio.thumbs[0].file_id)
            except:
                thumb = None

            await bot.send_audio(
                message.chat.id, file, caption=msg.caption,
                caption_entities=msg.caption_entities, reply_to_message_id=message.id,
                progress=progress, progress_args=[message, "up"]
            )

        elif msg_type == "Photo":
            await bot.send_photo(
                message.chat.id, file, caption=msg.caption,
                caption_entities=msg.caption_entities, reply_to_message_id=message.id
            )

    finally:
        if thumb and os.path.exists(thumb):
            os.remove(thumb)
        if file and os.path.exists(file):
            os.remove(file)
        if os.path.exists(f'{message.id}upstatus.txt'):
            os.remove(f'{message.id}upstatus.txt')
            progress_start_time.pop(f"{message.id}up", None)

        await bot.delete_messages(message.chat.id, [smsg.id])


USAGE = """**FOR PUBLIC CHATS**

__just send post/s link__

**FOR PRIVATE CHATS**

__first send invite link of the chat (unnecessary if the account of string session already member of the chat)
then send post/s link__

**FOR BOT CHATS**

__send link with '/b/', bot's username and message id, you might want to install some unofficial client to get the id like below__

```
https://t.me/b/botusername/4321
```

**MULTI POSTS**

__send public/private posts link as explained above with formate "from - to" to send multiple messages like below__

```
https://t.me/xxxx/1001-1010

https://t.me/c/xxxx/101 - 120
```

__note that space in between doesn't matter__
"""

bot.run()
