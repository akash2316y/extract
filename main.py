import os
import json
import time
import threading

from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from flask import Flask

# ========== CONFIG ==========
with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var): 
    return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN") 
api_hash = getenv("HASH") 
api_id = getenv("ID")

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None

# ========== USAGE ==========
USAGE = """**FOR PUBLIC CHATS**

__just send post/s link__

**FOR PRIVATE CHATS**

__first send invite link of the chat (unnecessary if the account of string session already member of the chat)
then send post/s link__

**FOR BOT CHATS**

__send link with '/b/', bot's username and message id, you might want to install some unofficial client to get the id like below__

https://t.me/b/botusername/4321

**MULTI POSTS**

__send public/private posts link as explained above with formate "from - to" to send multiple messages like below__

https://t.me/xxxx/1001-1010 https://t.me/c/xxxx/101 - 120

__note that space in between doesn't matter__
"""

# ========== UTILS ==========
def downstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(3)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Downloaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

def upstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(3)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Uploaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as f:
        f.write(f"{current * 100 / total:.1f}%")

def get_message_type(msg):
    for attr, msg_type in [
        ('document', 'Document'),
        ('video', 'Video'),
        ('animation', 'Animation'),
        ('sticker', 'Sticker'),
        ('voice', 'Voice'),
        ('audio', 'Audio'),
        ('photo', 'Photo'),
        ('text', 'Text'),
    ]:
        if getattr(msg, attr, None):
            return msg_type
    return "Unknown"

# ========== HANDLERS ==========

@bot.on_message(filters.command("start"))
def start_handler(_, message):
    bot.send_message(
        message.chat.id,
        f"**›› Hᴇʏ {message.from_user.mention} ×**, I am Save Restricted Bot, I can send you restricted content by its post link\n\n{USAGE}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Update Channel", url="https://t.me/UnknownBotz"),
             InlineKeyboardButton("💬 Support Group", url="https://t.me/UnknownBotzChat")]
        ]),
        reply_to_message_id=message.id
    )

@bot.on_message(filters.command("help"))
async def help_handler(_, m):
    await m.reply_text(
        f"𝖧𝖾𝗒 {m.from_user.mention},\n\n"
        "›› 𝖨 𝖢𝖺𝗇 𝖠𝖼𝖼𝖾𝗉𝗍 𝖩𝗈𝗂𝗇 𝖱𝖾𝗊𝗎𝖾𝗌𝗍𝗌 𝖠𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒.\n"
        "›› 𝖨 𝖢𝖺𝗇 𝖠𝖼𝖼𝖾𝗉𝗍 𝖠𝗅𝗅 𝖯𝖾𝗇𝖽𝗂𝗇𝗀 𝖱𝖾𝗊𝗎𝖾𝗌𝗍𝗌.\n\n"
        "𝟏. 𝐇𝐨𝐰 𝐭𝐨 𝐚𝐜𝐜𝐞𝐩𝐭 𝐧𝐞𝐰 𝐣𝐨𝐢𝐧 𝐫𝐞𝐪𝐮𝐞𝐬𝐭𝐬?\n\n"
        "👉 𝖲𝗂𝗆𝗉𝗅𝗒 𝖺𝖽𝖽 𝗆𝖾 𝗂𝗇 𝗒𝗈𝗎 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗈𝗋 𝗀𝗋𝗈𝗎𝗉 𝖺𝗌 𝖠𝖽𝗆𝗂𝗇 𝗐𝗂𝗍𝗁 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇.\n\n"
        "𝟐. 𝐇𝐨𝐰 𝐭𝐨 𝐚𝐜𝐜𝐞𝐩𝐭 𝐩𝐞𝐧𝐝𝐢𝐧𝐠 𝐣𝐨𝐢𝐧 𝐫𝐞𝐪𝐮𝐞𝐬𝐭𝐬?\n\n"
        "👉 𝖥𝗂𝗋𝗌𝗍 𝖺𝖽𝖽 𝗆𝖾 𝖺𝗌 𝖺𝖽𝗆𝗂𝗇 𝗂𝗇 𝗒𝗈𝗎𝗋 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗈𝗋 𝗀𝗋𝗈𝗎𝗉.\n"
        "👉 𝖫𝗈𝗀𝗂𝗇 𝗎𝗌𝗂𝗇𝗀 /login\n"
        "👉 𝖴𝗌𝖾 /accept 𝗍𝗈 𝖺𝖼𝖼𝖾𝗉𝗍 𝖺𝗅𝗅 𝗉𝖾𝗇𝖽𝗂𝗇𝗀 𝗋𝖾𝗊𝗎𝖾𝗌𝗍𝗌\n"
        "👉 𝖴𝗌𝖾 /logout 𝗐𝗁𝖾𝗇 𝖽𝗈𝗇𝖾"
    )

@bot.on_message(filters.text)
def link_handler(_, message):
    text = message.text

    if "https://t.me/+" in text or "https://t.me/joinchat/" in text:
        if acc is None:
            bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
            return
        try:
            acc.join_chat(text)
            bot.send_message(message.chat.id, "**Chat Joined**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            bot.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            bot.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)
        except Exception as e:
            bot.send_message(message.chat.id, f"**Error**: __{e}__", reply_to_message_id=message.id)

    elif "https://t.me/" in text:
        datas = text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())
        toID = int(temp[1].strip()) if len(temp) > 1 else fromID

        for msgid in range(fromID, toID + 1):
            try:
                if "https://t.me/c/" in text:
                    chatid = int("-100" + datas[4])
                    if acc is None:
                        bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                        return
                    handle_private(message, chatid, msgid)

                elif "https://t.me/b/" in text:
                    username = datas[4]
                    if acc is None:
                        bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                        return
                    handle_private(message, username, msgid)

                else:
                    username = datas[3]
                    try:
                        msg = bot.get_messages(username, msgid)
                        if '?single' not in text:
                            bot.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                        else:
                            bot.copy_media_group(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    except UsernameNotOccupied:
                        bot.send_message(message.chat.id, "**Invalid Username**", reply_to_message_id=message.id)
                    except Exception:
                        if acc is None:
                            bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                            return
                        handle_private(message, username, msgid)

                time.sleep(3)
            except Exception as e:
                bot.send_message(message.chat.id, f"**Error**: {e}", reply_to_message_id=message.id)

def handle_private(message, chatid_or_username, msgid):
    msg = acc.get_messages(chatid_or_username, msgid)
    msg_type = get_message_type(msg)

    if msg_type == "Text":
        bot.send_message(message.chat.id, msg.text, entities=msg.entities, reply_to_message_id=message.id)
        return

    smsg = bot.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)
    threading.Thread(target=downstatus, args=(f'{message.id}downstatus.txt', smsg), daemon=True).start()
    file = acc.download_media(msg, progress=progress, progress_args=[message, "down"])
    os.remove(f'{message.id}downstatus.txt')

    threading.Thread(target=upstatus, args=(f'{message.id}upstatus.txt', smsg), daemon=True).start()
    thumb = None

    try:
        if msg_type in ["Document", "Video", "Audio"]:
            if hasattr(msg, 'document'):
                thumb = acc.download_media(msg.document.thumbs[0].file_id)
            elif hasattr(msg, 'video'):
                thumb = acc.download_media(msg.video.thumbs[0].file_id)
            elif hasattr(msg, 'audio'):
                thumb = acc.download_media(msg.audio.thumbs[0].file_id)
    except:
        pass

    send_func = {
        "Document": bot.send_document,
        "Video": bot.send_video,
        "Animation": bot.send_animation,
        "Sticker": bot.send_sticker,
        "Voice": bot.send_voice,
        "Audio": bot.send_audio,
        "Photo": bot.send_photo,
    }.get(msg_type, bot.send_document)

    kwargs = {
        "chat_id": message.chat.id,
        "reply_to_message_id": message.id,
        "progress": progress,
        "progress_args": [message, "up"]
    }

    if msg_type in ["Document", "Audio", "Video", "Voice"]:
        kwargs.update({
            "caption": msg.caption,
            "caption_entities": msg.caption_entities,
            "thumb": thumb
        })

    if msg_type == "Video":
        kwargs.update({
            "duration": msg.video.duration,
            "width": msg.video.width,
            "height": msg.video.height,
        })

    send_func(file, **kwargs)

    if thumb: os.remove(thumb)
    os.remove(file)
    if os.path.exists(f'{message.id}upstatus.txt'): os.remove(f'{message.id}upstatus.txt')
    bot.delete_messages(message.chat.id, smsg.id)

# ========== FLASK ==========
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is Running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host="0.0.0.0", port=port)

# ========== START ==========
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run()
