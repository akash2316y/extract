import os
import re
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from config import API_ID, API_HASH, ERROR_MESSAGE, DB_CHANNEL
from database.db import db
from TechVJ.strings import HELP_TXT

class batch_temp:
    IS_BATCH = {}

def extract_links(text):
    return re.findall(r"(https?://[^\s]+)", text)

def create_link_buttons(links):
    buttons = []
    for i, link in enumerate(links, 1):
        buttons.append([InlineKeyboardButton(f"\ud83d\udd17 Link {i}", url=link)])
    return InlineKeyboardMarkup(buttons)

def progress(current, total, message, type):
    with open(f"{message.id}{type}status.txt", "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

async def downstatus(client, statusfile, message, chat):
    while not os.path.exists(statusfile):
        await asyncio.sleep(1)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            await client.edit_message_text(chat, message.id, f"Downloaded: {txt}")
            await asyncio.sleep(1)
        except:
            await asyncio.sleep(1)

async def upstatus(client, statusfile, message, chat):
    while not os.path.exists(statusfile):
        await asyncio.sleep(1)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            await client.edit_message_text(chat, message.id, f"Uploaded: {txt}")
            await asyncio.sleep(1)
        except:
            await asyncio.sleep(1)

@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)

    buttons = [
        [InlineKeyboardButton("\u2764\ufe0f Developer", url="https://t.me/UpperAssam")],
        [
            InlineKeyboardButton("\ud83d\udd0d Support Group", url="https://t.me/UnknownBotzChat"),
            InlineKeyboardButton("\ud83e\udd16 Update Channel", url="https://t.me/UnknownBotz")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await client.send_message(
        chat_id=message.chat.id,
        text=f"<b>\ud83d\udc4b Hi {message.from_user.mention}, I am Save Restricted Content Bot.\n\nUse /login to access restricted content.\nCheck /help for usage instructions.</b>",
        reply_markup=reply_markup,
        reply_to_message_id=message.id
    )

@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await client.send_message(chat_id=message.chat.id, text=HELP_TXT)

@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    batch_temp.IS_BATCH[message.from_user.id] = True
    await client.send_message(chat_id=message.chat.id, text="Batch Successfully Cancelled.")

@Client.on_message(filters.text & filters.private)
async def handle_user_message(client: Client, message: Message):
    links = extract_links(message.text)

    if links:
        keyboard = create_link_buttons(links)

        await client.send_message(
            chat_id=message.chat.id,
            text="\ud83d\udcce Here are your extracted links:",
            reply_markup=keyboard,
            reply_to_message_id=message.id
        )

        user_mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        await client.send_message(
            chat_id=DB_CHANNEL,
            text=f"\ud83d\udc64 From: {user_mention}\n\n\ud83d\udcce Here are the forwarded links:",
            reply_markup=keyboard
        )
        return

    if "https://t.me/" not in message.text:
        return

    if batch_temp.IS_BATCH.get(message.from_user.id) == False:
        return await message.reply_text("One task is already processing. Use /cancel to stop it.")

    datas = message.text.split("/")
    temp = datas[-1].replace("?single", "").split("-")
    fromID = int(temp[0].strip())
    try:
        toID = int(temp[1].strip())
    except:
        toID = fromID

    batch_temp.IS_BATCH[message.from_user.id] = False

    user_data = await db.get_session(message.from_user.id)
    if user_data is None:
        await message.reply("Please /login to continue.")
        batch_temp.IS_BATCH[message.from_user.id] = True
        return

    try:
        acc = Client("saverestricted", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
        await acc.connect()
    except:
        batch_temp.IS_BATCH[message.from_user.id] = True
        return await message.reply("Session expired. Use /logout and /login again.")

    if "https://t.me/c/" in message.text:
        chatid = int("-100" + datas[4])
    else:
        chatid = datas[3]

    for msgid in range(fromID, toID + 1):
        if batch_temp.IS_BATCH.get(message.from_user.id):
            break

        try:
            await handle_private(client, acc, message, chatid, msgid)
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)
        await asyncio.sleep(1)

    batch_temp.IS_BATCH[message.from_user.id] = True

async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int):
    msg = await acc.get_messages(chatid, msgid)
    if not msg or msg.empty:
        return

    msg_type = get_message_type(msg)
    if not msg_type:
        return

    chat = message.chat.id
    smsg = await client.send_message(chat, 'Downloading', reply_to_message_id=message.id)
    asyncio.create_task(downstatus(client, f'{message.id}downstatus.txt', smsg, chat))

    try:
        file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])
        os.remove(f'{message.id}downstatus.txt')
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(chat, f"Error: {e}", reply_to_message_id=message.id)
        return await smsg.delete()

    asyncio.create_task(upstatus(client, f'{message.id}upstatus.txt', smsg, chat))

    caption = msg.caption or msg.text or ""
    buttons = []
    if msg.reply_markup and msg.reply_markup.inline_keyboard:
        for row in msg.reply_markup.inline_keyboard:
            btn_row = []
            for button in row:
                btn_row.append(InlineKeyboardButton(
                    text=button.text,
                    url=button.url,
                    callback_data=button.callback_data,
                    switch_inline_query=button.switch_inline_query,
                    switch_inline_query_current_chat=button.switch_inline_query_current_chat,
                    pay=button.pay,
                    login_url=button.login_url
                ))
            buttons.append(btn_row)

    send_args = dict(
        caption=caption,
        reply_to_message_id=message.id,
        parse_mode=enums.ParseMode.MARKDOWN,
        progress=progress,
        progress_args=[message, "up"]
    )

    try:
        send_func = getattr(client, f"send_{msg_type.lower()}", None)
        if send_func:
            await send_func(chat, file, **send_args, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
            await send_func(DB_CHANNEL, file, caption=caption, parse_mode=enums.ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(chat, f"Error: {e}", reply_to_message_id=message.id)

    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
    if os.path.exists(file):
        os.remove(file)

    await client.delete_messages(chat, [smsg.id])

def get_message_type(msg):
    for attr in ["document", "video", "animation", "sticker", "voice", "audio", "photo", "text"]:
        if getattr(msg, attr, None):
            return attr.capitalize()
    return None


#Here's your updated bot code with full button support — including forwarding reply buttons like 480p | 720p | 1080p, etc. If you need deployment instructions or a requirements.txt, let me know.

