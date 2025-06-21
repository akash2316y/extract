import os
import json
import time
import threading

from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load config
with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var): return os.environ.get(var) or DATA.get(var, None)

# Bot config
api_id = getenv("ID")
api_hash = getenv("HASH")
bot_token = getenv("TOKEN")
string_session = getenv("STRING")
force_channel = getenv("FORCE_CHANNEL")  # e.g., "@yourchannel"

# Global storage for cancel command
active_tasks = {}

# Bot clients
bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=string_session) if string_session else None
if acc: acc.start()

# Usage text
USAGE = """
**FOR PUBLIC CHATS**
Send the post link.

**FOR PRIVATE CHATS**
Send the invite link (only needed if account isn't already in chat), then the post link.

**FOR BOT CHATS**
Use this format: `https://t.me/b/botusername/1234`

**MULTIPLE POSTS**
Use `from-to` format:
`https://t.me/xxxx/1001-1010`
`https://t.me/c/xxxx/101 - 120`
"""

# Flask app for uptime
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running 24/7!"

def run_flask(): app.run(host="0.0.0.0", port=8080)

# Force subscription check
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(force_channel, user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

# Cancel command
@bot.on_message(filters.command("cancel"))
def cancel_upload(_, message):
    user_id = message.from_user.id
    if user_id in active_tasks:
        active_tasks[user_id] = "cancel"
        message.reply_text("🚫 Task cancelled.")
    else:
        message.reply_text("❌ No active task found.")

# Start command
@bot.on_message(filters.command("start"))
def start(_, message):
    user_id = message.from_user.id
    if force_channel and not check_subscription(user_id):
        join_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{force_channel.lstrip('@')}")]])
        return message.reply_text("🚫 Join our channel first to use this bot.", reply_markup=join_button)

    message.reply_text(f"👋 Hi {message.from_user.mention}, I can fetch restricted Telegram posts.\n\n{USAGE}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Source Code", url="https://github.com/bipinkrish/Save-Restricted-Bot")]]))

# Progress tracking
def progress(current, total, message, type):
    with open(f"{message.id}{type}.txt", "w") as f:
        f.write(f"{current * 100 / total:.1f}%")

# Download/Upload status
def track_status(statusfile, message, prefix):
    while not os.path.exists(statusfile): time.sleep(1)
    while os.path.exists(statusfile):
        try:
            with open(statusfile) as f:
                pct = f.read()
            bot.edit_message_text(message.chat.id, message.id, f"{prefix} : **{pct}**")
            time.sleep(5)
        except: time.sleep(2)

# Handle text messages
@bot.on_message(filters.text)
def process_text(_, message):
    user_id = message.from_user.id

    if force_channel and not check_subscription(user_id):
        join_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{force_channel.lstrip('@')}")]])
        return message.reply_text("🚫 Join our channel first to use this bot.", reply_markup=join_button)

    text = message.text.strip()

    # Chat invite
    if "https://t.me/+" in text or "joinchat" in text:
        if not acc: return message.reply_text("⚠️ String session not set.")
        try:
            acc.join_chat(text)
            return message.reply_text("✅ Chat Joined.")
        except UserAlreadyParticipant:
            return message.reply_text("✅ Already a member.")
        except InviteHashExpired:
            return message.reply_text("❌ Invalid invite link.")
        except Exception as e:
            return message.reply_text(f"❌ Error: {e}")

    # Message links
    if "https://t.me/" in text:
        parts = text.split("/")
        last = parts[-1].replace("?single", "")
        try:
            ids = list(map(int, last.split("-")))
        except: return message.reply_text("❌ Invalid message ID range.")

        start_id = ids[0]
        end_id = ids[-1]

        for msg_id in range(start_id, end_id + 1):
            if "t.me/c/" in text:
                chat_id = int("-100" + parts[4])
            elif "t.me/b/" in text:
                chat_id = parts[4]
            else:
                chat_id = parts[3]

            if acc is None:
                return message.reply_text("⚠️ String session not set.")

            active_tasks[user_id] = "running"
            try:
                send_restricted(message, chat_id, msg_id, user_id)
            except Exception as e:
                message.reply_text(f"❌ Error: {e}")
            finally:
                active_tasks.pop(user_id, None)

            time.sleep(2)

# Send restricted messages
def send_restricted(message, chat_id, msg_id, user_id):
    msg = acc.get_messages(chat_id, msg_id)
    mtype = get_msg_type(msg)

    if active_tasks.get(user_id) == "cancel":
        return

    if mtype == "Text":
        return bot.send_message(message.chat.id, msg.text, reply_to_message_id=message.id)

    status_msg = bot.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)

    d_thread = threading.Thread(target=track_status, args=(f"{message.id}down.txt", status_msg, "📥 Downloaded"), daemon=True)
    d_thread.start()

    file = acc.download_media(msg, progress=progress, progress_args=(message, "down"))
    os.remove(f"{message.id}down.txt")

    u_thread = threading.Thread(target=track_status, args=(f"{message.id}up.txt", status_msg, "📤 Uploaded"), daemon=True)
    u_thread.start()

    kwargs = {
        "caption": msg.caption,
        "caption_entities": msg.caption_entities,
        "reply_to_message_id": message.id,
        "progress": progress,
        "progress_args": (message, "up"),
    }

    thumb = None
    try:
        if mtype in ["Document", "Audio", "Video"]:
            thumb = acc.download_media(getattr(msg, mtype.lower()).thumbs[0].file_id)
            kwargs["thumb"] = thumb
    except: pass

    if mtype == "Document":
        bot.send_document(message.chat.id, file, **kwargs)
    elif mtype == "Video":
        bot.send_video(message.chat.id, file, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, **kwargs)
    elif mtype == "Audio":
        bot.send_audio(message.chat.id, file, **kwargs)
    elif mtype == "Voice":
        bot.send_voice(message.chat.id, file, **kwargs)
    elif mtype == "Photo":
        bot.send_photo(message.chat.id, file, **kwargs)
    elif mtype == "Animation":
        bot.send_animation(message.chat.id, file, **kwargs)
    elif mtype == "Sticker":
        bot.send_sticker(message.chat.id, file, reply_to_message_id=message.id)

    if thumb: os.remove(thumb)
    os.remove(file)
    if os.path.exists(f"{message.id}up.txt"): os.remove(f"{message.id}up.txt")
    bot.delete_messages(message.chat.id, [status_msg.id])

# Determine message type
def get_msg_type(msg):
    for attr in ["document", "video", "animation", "sticker", "voice", "audio", "photo"]:
        if getattr(msg, attr, None): return attr.capitalize()
    if msg.text: return "Text"
    return "Unknown"

# Run everything
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run()
