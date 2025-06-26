import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import os
import threading
import json
from flask import Flask

with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")
IS_FSUB = getenv("FSUB") == "True"

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss is not None:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None

# ----------------- STATUS HANDLERS -----------------

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

# ----------------- COMMANDS -----------------

@bot.on_message(filters.command(["start"]))
async def send_start(client, message):
    if IS_FSUB and not await get_fsub(client, message):
        return

    await client.send_message(
        message.chat.id,
        f"›› Hᴇʏ {message.from_user.mention} ×,\n\n{USAGE}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("𝖴𝗉𝖽𝖺𝗍𝖾", url="https://t.me/UnknownBotz"),
                InlineKeyboardButton("𝖲𝗎𝗉𝗉𝗈𝗋𝗍", url="https://t.me/UnknownBotzChat")
            ]
        ]),
        reply_to_message_id=message.id
    )

@bot.on_message(filters.text)
async def save(client, message):
    if IS_FSUB and not await get_fsub(client, message):
        return

    print(message.text)

    if "https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text:
        if acc is None:
            await client.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
            return

        try:
            try:
                acc.join_chat(message.text)
            except Exception as e:
                await client.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)
                return
            await client.send_message(message.chat.id, "**Chat Joined**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            await client.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            await client.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)

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
                    await client.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                    return
                handle_private(message, chatid, msgid)

            elif "https://t.me/b/" in message.text:
                username = datas[4]
                if acc is None:
                    await client.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                    return
                try:
                    handle_private(message, username, msgid)
                except Exception as e:
                    await client.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)
            else:
                username = datas[3]
                try:
                    msg = client.get_messages(username, msgid)
                except UsernameNotOccupied:
                    await client.send_message(message.chat.id, "**The username is not occupied by anyone**", reply_to_message_id=message.id)
                    return
                try:
                    if '?single' not in message.text:
                        await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    else:
                        await client.copy_media_group(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                except:
                    if acc is None:
                        await client.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                        return
                    try:
                        handle_private(message, username, msgid)
                    except Exception as e:
                        await client.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)

            time.sleep(3)

# ----------------- PRIVATE HANDLER -----------------

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
        bot.send_document(message.chat.id, file, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        if thumb:
            os.remove(thumb)

    elif "Video" == msg_type:
        try:
            thumb = acc.download_media(msg.video.thumbs[0].file_id)
        except:
            thumb = None
        bot.send_video(message.chat.id, file, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        if thumb:
            os.remove(thumb)

    elif "Animation" == msg_type:
        bot.send_animation(message.chat.id, file, reply_to_message_id=message.id)

    elif "Sticker" == msg_type:
        bot.send_sticker(message.chat.id, file, reply_to_message_id=message.id)

    elif "Voice" == msg_type:
        bot.send_voice(message.chat.id, file, caption=msg.caption, thumb=None, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])

    elif "Audio" == msg_type:
        try:
            thumb = acc.download_media(msg.audio.thumbs[0].file_id)
        except:
            thumb = None
        bot.send_audio(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        if thumb:
            os.remove(thumb)

    elif "Photo" == msg_type:
        bot.send_photo(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id)

    os.remove(file)
    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
    bot.delete_messages(message.chat.id, [smsg.id])

# ----------------- HELPER -----------------

def get_message_type(msg):
    try: return "Document" if msg.document else None
    except: pass
    try: return "Video" if msg.video else None
    except: pass
    try: return "Animation" if msg.animation else None
    except: pass
    try: return "Sticker" if msg.sticker else None
    except: pass
    try: return "Voice" if msg.voice else None
    except: pass
    try: return "Audio" if msg.audio else None
    except: pass
    try: return "Photo" if msg.photo else None
    except: pass
    try: return "Text" if msg.text else None
    except: pass


USAGE =  """**𝖲𝖨𝖭𝖦𝖫𝖤 𝖯𝖮𝖲𝖳  𝖥𝖮𝖱 𝖯𝖴𝖡𝖫𝖨𝖢 𝖢𝖧𝖠𝖭𝖭𝖤𝖫**
𝖩𝗎𝗌𝗍 𝗌𝖾𝗇𝖽 𝗉𝗈𝗌𝗍 𝗅𝗂𝗇𝗄...

**𝖲𝖨𝖭𝖦𝖫𝖤 𝖯𝖮𝖲𝖳 𝖥𝖮𝖱 𝖯𝖱𝖨𝖵𝖠𝖳𝖤 𝖢𝖧𝖠𝖭𝖭𝖤𝖫**
𝖥𝗋𝗂𝗌𝗍 𝗌𝖾𝗇𝖽 𝗂𝗇𝗏𝗂𝗍𝖾 𝗅𝗂𝗇𝗄 𝗍𝗁𝖾 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗈𝗋 𝗀𝗋𝗈𝗎𝗉 𝗍𝗁𝖾𝗇 𝗌𝖾𝗇𝖽 𝗉𝗈𝗌𝗍 𝗅𝗂𝗇𝗄

**𝖬𝖴𝖫𝖳𝖨 𝖯𝖮𝖲𝖳𝖲 𝖯𝖴𝖡𝖫𝖨𝖢/𝖯𝖱𝖨𝖵𝖠𝖳𝖤 𝖢𝖧𝖠𝖭𝖭𝖤𝖫**
𝖲𝖾𝗇𝖽 𝗉𝗎𝖻𝗅𝗂𝖼/𝗉𝗋𝗂𝗏𝖺𝗍𝖾 𝗉𝗈𝗌𝗍𝗌 𝗅𝗂𝗇𝗄 𝖺𝗌 𝖾𝗑𝗉𝗅𝖺𝗂𝗇𝖾𝖽 𝖺𝖻𝗈𝗏𝖾 𝗐𝗂𝗍𝗁 𝖿𝗈𝗋𝗆𝖺𝗍𝖾 "𝖿𝗋𝗈𝗆 - 𝗍𝗈" 𝗍𝗈 𝗌𝖾𝗇𝖽 𝗆𝗎𝗅𝗍𝗂𝗉𝗅𝖾 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌 𝗅𝗂𝗄𝖾 𝖻𝖾𝗅𝗈𝗐
`𝗁𝗍𝗍𝗉𝗌://𝗍.𝗆𝖾/𝗑𝗑𝗑𝗑/1001-1010`
`𝗁𝗍𝗍𝗉𝗌://𝗍.𝗆𝖾/𝖼/𝗑𝗑𝗑𝗑/101 - 120`

𝖭𝗈𝗍𝖾 𝗍𝗁𝖺𝗍 𝗌𝗉𝖺𝖼𝖾 𝗂𝗇 𝖻𝖾𝗍𝗐𝖾𝖾𝗇 𝖽𝗈𝖾𝗌𝗇'𝗍 𝗆𝖺𝗍𝗍𝖾𝗋 ‼️"""



# ----------------- FLASK KEEP-ALIVE -----------------

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is Running 24/7!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run()

