import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
import asyncio
import time
import os
import threading
import json

# Load configuration
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

# Progress tracking functions

def downstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Downloaded__: **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)


def upstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Uploaded__: **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)


def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as f:
        f.write(f"{current * 100 / total:.1f}%")

# Start command

@bot.on_message(filters.command(["start"]))
async def start_command(client, message):
    await bot.send_message(
        message.chat.id,
        f"👋 Hi **{message.from_user.mention}**, I can send you restricted content by its post link.\n\n{USAGE}",
        reply_to_message_id=message.id
    )

# Main handler

@bot.on_message(filters.text)
async def main_handler(client, message):
    text = message.text

    if "https://t.me/+" in text or "https://t.me/joinchat/" in text:
        if acc is None:
            await bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
            return
        try:
            await acc.join_chat(text)
            await bot.send_message(message.chat.id, "**Chat Joined**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            await bot.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            await bot.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)
        except Exception as e:
            await bot.send_message(message.chat.id, f"**Error**: __{e}__", reply_to_message_id=message.id)
        return

    elif "https://t.me/" in text:
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
                if acc is None:
                    await bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                    return
                await handle_private(message, chatid, msgid)
            else:
                username = parts[3]
                try:
                    msg = await bot.get_messages(username, msgid)
                    await bot.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
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

    smsg = await bot.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)

    asyncio.create_task(asyncio.to_thread(downstatus, f'{message.id}downstatus.txt', smsg))
    file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])

    if os.path.exists(f'{message.id}downstatus.txt'):
        os.remove(f'{message.id}downstatus.txt')

    asyncio.create_task(asyncio.to_thread(upstatus, f'{message.id}upstatus.txt', smsg))

    thumb = None

    try:
        if msg_type == "Document":
            try:
                thumb = await acc.download_media(msg.document.thumbs[0].file_id)
            except:
                pass
            await acc.send_document(message.chat.id, file, thumb=thumb, caption=msg.caption,
                                     caption_entities=msg.caption_entities, reply_to_message_id=message.id,
                                     progress=progress, progress_args=[message, "up"])

        elif msg_type == "Video":
            try:
                thumb = await acc.download_media(msg.video.thumbs[0].file_id)
            except:
                pass
            await acc.send_video(message.chat.id, file, duration=msg.video.duration, width=msg.video.width,
                                 height=msg.video.height, thumb=thumb, caption=msg.caption,
                                 caption_entities=msg.caption_entities, reply_to_message_id=message.id,
                                 progress=progress, progress_args=[message, "up"])

        elif msg_type == "Animation":
            await acc.send_animation(message.chat.id, file, reply_to_message_id=message.id)

        elif msg_type == "Sticker":
            await acc.send_sticker(message.chat.id, file, reply_to_message_id=message.id)

        elif msg_type == "Voice":
            await acc.send_voice(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])

        elif msg_type == "Audio":
            try:
                thumb = await acc.download_media(msg.audio.thumbs[0].file_id)
            except:
                pass
            await acc.send_audio(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])

        elif msg_type == "Photo":
            await acc.send_photo(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities,
                                 reply_to_message_id=message.id)

    finally:
        if thumb and os.path.exists(thumb):
            os.remove(thumb)
        if file and os.path.exists(file):
            os.remove(file)
        if os.path.exists(f'{message.id}upstatus.txt'):
            os.remove(f'{message.id}upstatus.txt')
        await bot.delete_messages(message.chat.id, [smsg.id])


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


USAGE = """**FOR PUBLIC CHATS**

__just send post/s link__

**FOR PRIVATE CHATS**

__first send invite link of the chat (unnecessary if the account of string session already member of the chat)
then send post/s link__

**FOR BOT CHATS**

__send link with '/b/', bot's username and message id__

```
https://t.me/b/botusername/4321
```

**MULTI POSTS**

__send public/private posts link as explained above with format "from - to"__

```
https://t.me/xxxx/1001-1010

https://t.me/c/xxxx/101-120
```

__note that spaces don't matter__
"""

bot.run()
