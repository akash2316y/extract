import pyrogram
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import time
import os
import threading
import json
from flask import Flask

# Load config
with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN") 
api_hash = getenv("HASH") 
api_id = getenv("ID")

# Bot client
bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Optional user session
ss = getenv("STRING")
if ss is not None:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None

# Status display
def downstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)
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
        time.sleep(1)
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

# Start command
@bot.on_message(filters.command(["start"]))
async def send_start(client, message):
    await bot.send_message(
        message.chat.id,
        f"""<b><i>›› Hᴇʏ {message.from_user.mention} ×</i></b>\n
𝖲𝗂𝗆𝗉𝗅𝗒 𝖲𝖾𝗇𝖽 𝗆𝖾 𝖠𝗇𝗒 𝖳𝗒𝗉𝖾 𝗈𝖿 𝖱𝖾𝗌𝗍𝗋𝗂𝖼𝗍𝖾𝖽 𝖫𝗂𝗇𝗄  
𝖯𝗈𝗌𝗍 𝖥𝗋𝗈𝗆 𝖯𝗎𝖻𝗅𝗂𝖼 & 𝖯𝗋𝗂𝗏𝖺𝗍𝖾 𝖢𝗁𝖺𝗇𝗇𝖾𝗅 𝗈𝗋 𝖦𝗋𝗈𝗎𝗉‼️""",
        reply_markup=start_buttons(),
        reply_to_message_id=message.id,
        parse_mode=ParseMode.HTML
    )
	
def start_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("𝖴𝗉𝖽𝖺𝗍𝖾", url="https://t.me/UnknowBotz"),
            InlineKeyboardButton("𝖲𝗎𝗉𝗉𝗈𝗋𝗍", url="https://t.me/UnknowBotzChat")
        ],
        [
            InlineKeyboardButton("𝖧𝖾𝗅𝗉", callback_data="help"),
            InlineKeyboardButton("𝖠𝖻𝗈𝗎𝗍", callback_data="about")
        ]
    ])

@bot.on_callback_query(filters.regex("help"))
async def help_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "**🔰 Help Menu**\n\nJust send me any post link from a private channel or group, and I will fetch it for you (if accessible).",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("𝖡𝖺𝖼𝗄", callback_data="back"),
                InlineKeyboardButton("𝖢𝗅𝗈𝗌𝖾", callback_data="close")
            ]
        ])
    )
    await asyncio.sleep(300)
    try:
        await client.delete_messages(chat_id=callback_query.message.chat.id, message_ids=callback_query.message.id)
    except:
        pass

@bot.on_callback_query(filters.regex("about"))
async def about_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "○ 𝖢𝗋𝖾𝖺𝗍𝗈𝗋 :<a href='https://t.me/AlwaysToHelpBot'>𝖴𝗇𝗄𝗇𝗈𝗐𝗇</a>\n○ 𝖫𝖺𝗇𝗀𝗎𝖺𝗀𝖾 :<code>𝖯𝗒𝗍𝗁𝗈𝗇</code>\n○ 𝖫𝗂𝖻𝗋𝖺𝗋𝗒 :<a href='https://docs.pyrogram.org/'>𝖯𝗒𝗋𝗈𝗀𝗋𝖺𝗆</a>\n○ 𝖲𝗈𝗎𝗋𝖼𝖾 𝖢𝗈𝖽𝖾 :<a href='https://t.me/+_1Bx_kts2ocxMDE9'>𝖢𝗅𝗂𝖼𝗄 𝗁𝖾𝗋𝖾</a>",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("𝖡𝖺𝖼𝗄", callback_data="back"),
                InlineKeyboardButton("𝖢𝗅𝗈𝗌𝖾", callback_data="close")
            ]
        ])
    )
    await asyncio.sleep(300)
    try:
        await client.delete_messages(chat_id=callback_query.message.chat.id, message_ids=callback_query.message.id)
    except:
        pass

@bot.on_callback_query(filters.regex("back"))
async def back_callback(client, callback_query: CallbackQuery):
    try:
        await callback_query.message.edit_text(
            f"""<b><blockquote>›› Hᴇʏ {callback_query.from_user.mention} ×</blockquote></b>\n
𝖲𝗂𝗆𝗉𝗅𝗒 𝖲𝖾𝗇𝖽 𝗆𝖾 𝖠𝗇𝗒 𝖳𝗒𝗉𝖾 𝗈𝖿 𝖱𝖾𝗌𝗍𝗋𝗂𝖼𝗍𝖾𝖽 𝖫𝗂𝗇𝗄
𝖯𝗈𝗌𝗍 𝖥𝗋𝗈𝗆 𝖯𝗎𝖻𝗅𝗂𝖼 & 𝖯𝗋𝗂𝗏𝖺𝗍𝖾 𝖢𝗁𝖺𝗇𝗇𝖾𝗅 𝗈𝗋 𝖦𝗋𝗈𝗎𝗉‼️""",
            reply_markup=start_buttons(),
            parse_mode=ParseMode.HTML
        )
    except MessageNotModified:
        pass

@bot.on_callback_query(filters.regex("close"))
async def close_callback(client, callback_query: CallbackQuery):
    try:
        await callback_query.message.delete()
    except:
        pass

# Flask to keep alive (optional, for Koyeb)
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is Running 24/7!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# Start
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run()
	    
