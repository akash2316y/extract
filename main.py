import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied, UserNotParticipant, ChatAdminRequired, PeerIdInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import time
import os
import threading
import json

# Load config
with open('config.json', 'r') as f: DATA = json.load(f)
def getenv(var): return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN") 
api_hash = getenv("HASH") 
api_id = getenv("ID")
FORCE_SUB_CHANNEL = getenv("FORCE_SUB_CHANNEL")

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss is not None:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None

# Force Subscribe check
def is_subscribed(user_id):
    if not FORCE_SUB_CHANNEL or FORCE_SUB_CHANNEL.lower() == "none":
        return True  # No force sub required

    try:
        member = bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except (UserNotParticipant, ChatAdminRequired, PeerIdInvalid):
        return False
    except Exception as e:
        print(f"ForceSub Error: {e}")
        return False

def force_sub_reply(message):
    try:
        link = f"https://t.me/{FORCE_SUB_CHANNEL.strip('@')}"
    except:
        link = "https://t.me/yourchannel"
    bot.send_message(
        chat_id=message.chat.id,
        text=f"🚫 To use this bot, please join our channel first:\n\n👉 [Join Now]({link})",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=link)]]),
        disable_web_page_preview=True,
        reply_to_message_id=message.id
    )

# download status
def downstatus(statusfile,message):
    while True:
        if os.path.exists(statusfile): break
    time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile,"r") as downread:
            txt = downread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Downloaded__ : **{txt}**")
            time.sleep(10)
        except: time.sleep(5)

# upload status
def upstatus(statusfile,message):
    while True:
        if os.path.exists(statusfile): break
    time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile,"r") as upread:
            txt = upread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Uploaded__ : **{txt}**")
            time.sleep(10)
        except: time.sleep(5)

# progress writer
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt',"w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

# Start command
@bot.on_message(filters.command(["start"]))
def send_start(client, message):
    if not is_subscribed(message.from_user.id):
        return force_sub_reply(message)
    bot.send_message(message.chat.id, f"__👋 Hi **{message.from_user.mention}**, I am Save Restricted Bot, I can send you restricted content by its post link__\n\n{USAGE}",
        reply_markup=InlineKeyboardMarkup([[ InlineKeyboardButton("🌐 Source Code", url="https://github.com/bipinkrish/Save-Restricted-Bot")]]),
        reply_to_message_id=message.id)

@bot.on_message(filters.text)
def save(client, message):
    if not is_subscribed(message.from_user.id):
        return force_sub_reply(message)

    print(message.text)

    # Chat join link
    if "https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text:
        if acc is None:
            return bot.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)

        try:
            try: acc.join_chat(message.text)
            except Exception as e:
                return bot.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)
            return bot.send_message(message.chat.id, "**Chat Joined**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            return bot.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            return bot.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)

    elif "https://t.me/" in message.text:
        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())
        try: toID = int(temp[1].strip())
        except: toID = fromID

        for msgid in range(fromID, toID+1):
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])
                if acc is None:
                    return bot.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
                handle_private(message, chatid, msgid)

            elif "https://t.me/b/" in message.text:
                username = datas[4]
                if acc is None:
                    return bot.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
                try: handle_private(message, username, msgid)
                except Exception as e:
                    bot.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)

            else:
                username = datas[3]
                try: msg = bot.get_messages(username, msgid)
                except UsernameNotOccupied:
                    return bot.send_message(message.chat.id, f"**Username is not valid**", reply_to_message_id=message.id)
                try:
                    if '?single' not in message.text:
                        bot.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    else:
                        bot.copy_media_group(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                except:
                    if acc is None:
                        return bot.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
                    try: handle_private(message, username, msgid)
                    except Exception as e:
                        bot.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)
            time.sleep(3)

# Message handler
def handle_private(message, chatid, msgid):
    msg = acc.get_messages(chatid, msgid)
    msg_type = get_message_type(msg)

    if msg_type == "Text":
        return bot.send_message(message.chat.id, msg.text, entities=msg.entities, reply_to_message_id=message.id)

    smsg = bot.send_message(message.chat.id, '__Downloading__', reply_to_message_id=message.id)
    dosta = threading.Thread(target=lambda: downstatus(f'{message.id}downstatus.txt', smsg), daemon=True)
    dosta.start()

    file = acc.download_media(msg, progress=progress, progress_args=[message, "down"])
    os.remove(f'{message.id}downstatus.txt')

    upsta = threading.Thread(target=lambda: upstatus(f'{message.id}upstatus.txt', smsg), daemon=True)
    upsta.start()

    thumb = None
    try:
        if hasattr(msg, 'video'):
            thumb = acc.download_media(msg.video.thumbs[0].file_id)
        elif hasattr(msg, 'audio'):
            thumb = acc.download_media(msg.audio.thumbs[0].file_id)
        elif hasattr(msg, 'document'):
            thumb = acc.download_media(msg.document.thumbs[0].file_id)
    except: pass

    if msg_type == "Document":
        bot.send_document(message.chat.id, file, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
    elif msg_type == "Video":
        bot.send_video(message.chat.id, file, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
    elif msg_type == "Photo":
        bot.send_photo(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id)
    elif msg_type == "Audio":
        bot.send_audio(message.chat.id, file, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
    elif msg_type == "Voice":
        bot.send_voice(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id)
    elif msg_type == "Sticker":
        bot.send_sticker(message.chat.id, file, reply_to_message_id=message.id)
    elif msg_type == "Animation":
        bot.send_animation(message.chat.id, file, reply_to_message_id=message.id)

    os.remove(file)
    if os.path.exists(f'{message.id}upstatus.txt'): os.remove(f'{message.id}upstatus.txt')
    bot.delete_messages(message.chat.id, [smsg.id])

def get_message_type(msg):
    if msg.document: return "Document"
    if msg.video: return "Video"
    if msg.animation: return "Animation"
    if msg.sticker: return "Sticker"
    if msg.voice: return "Voice"
    if msg.audio: return "Audio"
    if msg.photo: return "Photo"
    if msg.text: return "Text"
    return "Unknown"

USAGE = """**FOR PUBLIC CHATS**
Just send post link

**FOR PRIVATE CHATS**
First send invite link if not joined, then send post link

**FOR BOT CHATS**
Use format:

https://t.me/b/botusername/1234

**MULTI POST**
Use format:

https://t.me/channel/100-110

"""

# Flask WebServer
from flask import Flask
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Bot is Running 24/7!"
def run_flask(): app_flask.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run()
