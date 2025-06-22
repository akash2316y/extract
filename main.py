import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading
import time
import os
import json

# Load config
with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")
FORCE_JOIN_CHANNEL = "kids_coder"  # 👈 Change to your channel username

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss is not None:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None

# Force Join Checker
async def is_user_joined(client, user_id):
    try:
        member = await client.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Start command
@bot.on_message(filters.command(["start"]))
async def send_start(client, message):
    if not await is_user_joined(client, message.from_user.id):
        await bot.send_message(
            message.chat.id,
            f"🚫 To use this bot, please join @{FORCE_JOIN_CHANNEL} first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL}")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_check")]
            ]),
            reply_to_message_id=message.id
        )
        return

    await bot.send_message(
        message.chat.id,
        f"👋 Hi **{message.from_user.mention}**, I am Save Restricted Bot, I can send you restricted content by its post link.\n\n{USAGE}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Source Code", url="https://github.com/bipinkrish/Save-Restricted-Bot")]
        ]),
        reply_to_message_id=message.id
    )

# Refresh button handler
@bot.on_callback_query(filters.regex("refresh_check"))
async def refresh_check(client, callback_query):
    if await is_user_joined(client, callback_query.from_user.id):
        await callback_query.message.edit_text("✅ You have joined the channel. Now you can use the bot.\nSend a post link to begin.")
    else:
        await callback_query.answer("❌ You haven't joined yet!", show_alert=True)

# Handle user links
@bot.on_message(filters.text)
def save(client, message):
    print(message.text)

    if "https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text:
        if acc is None:
            bot.send_message(message.chat.id, "❌ String Session is not Set", reply_to_message_id=message.id)
            return
        try:
            try:
                acc.join_chat(message.text)
            except Exception as e:
                bot.send_message(message.chat.id, f"**Error**: __{e}__", reply_to_message_id=message.id)
                return
            bot.send_message(message.chat.id, "✅ Chat Joined", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            bot.send_message(message.chat.id, "✅ Already in Chat", reply_to_message_id=message.id)
        except InviteHashExpired:
            bot.send_message(message.chat.id, "❌ Invalid Link", reply_to_message_id=message.id)

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
                    bot.send_message(message.chat.id, "❌ String Session is not Set", reply_to_message_id=message.id)
                    return
                handle_private(message, chatid, msgid)

            elif "https://t.me/b/" in message.text:
                username = datas[4]
                if acc is None:
                    bot.send_message(message.chat.id, "❌ String Session is not Set", reply_to_message_id=message.id)
                    return
                try:
                    handle_private(message, username, msgid)
                except Exception as e:
                    bot.send_message(message.chat.id, f"**Error**: __{e}__", reply_to_message_id=message.id)

            else:
                username = datas[3]
                try:
                    msg = bot.get_messages(username, msgid)
                except UsernameNotOccupied:
                    bot.send_message(message.chat.id, "❌ Username is not occupied", reply_to_message_id=message.id)
                    return
                try:
                    if '?single' not in message.text:
                        bot.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    else:
                        bot.copy_media_group(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                except:
                    if acc is None:
                        bot.send_message(message.chat.id, "❌ String Session is not Set", reply_to_message_id=message.id)
                        return
                    try:
                        handle_private(message, username, msgid)
                    except Exception as e:
                        bot.send_message(message.chat.id, f"**Error**: __{e}__", reply_to_message_id=message.id)
            time.sleep(3)

# Private handler
def handle_private(message, chatid, msgid):
    msg = acc.get_messages(chatid, msgid)
    msg_type = get_message_type(msg)

    if "Text" == msg_type:
        bot.send_message(message.chat.id, msg.text, entities=msg.entities, reply_to_message_id=message.id)
        return

    smsg = bot.send_message(message.chat.id, '__Downloading__', reply_to_message_id=message.id)
    dosta = threading.Thread(target=lambda: downstatus(f'{message.id}downstatus.txt', smsg), daemon=True)
    dosta.start()
    file = acc.download_media(msg, progress=progress, progress_args=[message, "down"])
    os.remove(f'{message.id}downstatus.txt')

    upsta = threading.Thread(target=lambda: upstatus(f'{message.id}upstatus.txt', smsg), daemon=True)
    upsta.start()

    if "Document" == msg_type:
        try:
            thumb = acc.download_media(msg.document.thumbs[0].file_id)
        except:
            thumb = None
        bot.send_document(message.chat.id, file, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities,
                          reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        if thumb:
            os.remove(thumb)

    elif "Video" == msg_type:
        try:
            thumb = acc.download_media(msg.video.thumbs[0].file_id)
        except:
            thumb = None
        bot.send_video(message.chat.id, file, duration=msg.video.duration, width=msg.video.width,
                       height=msg.video.height, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities,
                       reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        if thumb:
            os.remove(thumb)

    elif "Photo" == msg_type:
        bot.send_photo(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id)

    os.remove(file)
    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
    bot.delete_messages(message.chat.id, [smsg.id])

# Message type checker
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
        msg.photo.file_id
        return "Photo"
    except:
        pass
    try:
        msg.text
        return "Text"
    except:
        pass

# Progress writers
def downstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Downloaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

def upstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Uploaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

# Flask
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is Running 24/7!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# Bot runner
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run()

USAGE = """**FOR PUBLIC CHATS**
Send the post link.

**FOR PRIVATE CHATS**
First send the chat invite link (if not already joined), then the post link.

**FOR BOT CHATS**
Use this format:

https://t.me/b/botusername/4321

**MULTIPLE POSTS**
Use format:

https://t.me/xxxx/1001-1010 https://t.me/c/xxxx/101-120

"""
