import os
import time
import asyncio
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup
from pyrogram.errors import FloodWait

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("SESSION_STRING")
DB_CHANNEL = int(os.environ.get("DB_CHANNEL"))

bot = Client("forward-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)


# --- HELPERS ---
def get_type(msg):
    if msg.text:
        return "Text", None, None
    if msg.sticker:
        return "Sticker", None, None
    if msg.document:
        return "Document", msg.document.file_name, msg.document.file_size
    if msg.video:
        return "Video", msg.video.file_name, msg.video.file_size
    if msg.audio:
        return "Audio", msg.audio.file_name, msg.audio.file_size
    if msg.photo:
        return "Photo", None, None
    if msg.voice:
        return "Voice", None, None
    if msg.animation:
        return "Animation", None, None
    return None, None, None


def extract_buttons(msg):
    if msg.reply_markup and isinstance(msg.reply_markup, InlineKeyboardMarkup):
        return msg.reply_markup
    return None


async def update_progress(message, current_fn, total, start_time, action, filename):
    while True:
        current = current_fn()
        now = time.time()
        elapsed = now - start_time
        speed = current / elapsed if elapsed > 0 else 0
        percent = (current / total) * 100 if total else 0
        eta = (total - current) / speed if speed > 0 else 0
        try:
            await message.edit(
                f"{action} `{filename}`\n"
                f"Progress: {percent:.1f}%\n"
                f"Speed: {speed/1024:.2f} KB/s\n"
                f"ETA: {int(eta)}s"
            )
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass
        await asyncio.sleep(2)


# --- MAIN FORWARD FUNCTION ---
async def forward_message(m, chat_id, msg_id):
    if not user:
        await m.reply("❌ User session required.")
        return

    try:
        msg = await user.get_messages(chat_id, msg_id)
    except Exception as e:
        await m.reply(f"❌ Cannot fetch original message: {e}")
        return

    msg_type, filename, filesize = get_type(msg)
    markup = extract_buttons(msg)

    # ✅ Handle quoted/replied-to message
    reply_to = None
    if msg.reply_to_message:
        r_msg = msg.reply_to_message
        r_type, r_filename, _ = get_type(r_msg)

        try:
            if r_type == "Text" or not r_type:
                reply_to = await bot.send_message(
                    DB_CHANNEL,
                    (r_msg.text or r_msg.caption or "❌ Empty quote"),
                    entities=r_msg.entities,
                )
            elif r_type == "Sticker" and getattr(r_msg, "sticker", None):
                reply_to = await bot.send_sticker(DB_CHANNEL, r_msg.sticker.file_id)
            else:
                fpath = await user.download_media(r_msg, file_name="downloads/")
                send_func = {
                    "Document": bot.send_document,
                    "Video": bot.send_video,
                    "Audio": bot.send_audio,
                    "Photo": bot.send_photo,
                    "Voice": bot.send_voice,
                    "Animation": bot.send_animation,
                }.get(r_type)
                if send_func:
                    reply_to = await send_func(DB_CHANNEL, fpath, caption=r_msg.caption)
                os.remove(fpath)
        except Exception:
            pass

    # ✅ Handle Text
    if msg_type == "Text" or not msg_type:
        text = (msg.text or msg.caption or "").strip()
        if msg.forward_from:
            sender = f"{msg.forward_from.first_name} {msg.forward_from.last_name or ''}".strip()
            text = f"💬 Forwarded from {sender}:\n\n{text}"
        elif msg.forward_sender_name:
            text = f"💬 Forwarded from {msg.forward_sender_name}:\n\n{text}"

        if text:
            await bot.send_message(
                DB_CHANNEL,
                text,
                entities=msg.entities,
                reply_markup=markup,
                reply_to_message_id=reply_to.id if reply_to else None
            )
        return

    # ✅ Handle Stickers
    if msg_type == "Sticker" and getattr(msg, "sticker", None):
        await bot.send_sticker(
            DB_CHANNEL,
            msg.sticker.file_id,
            reply_markup=markup,
            reply_to_message_id=reply_to.id if reply_to else None
        )
        return

    # ✅ Handle Media (download + upload with progress)
    smsg = await m.reply("📥 Downloading...")
    downloaded = [0]
    start_time = time.time()

    async def download_cb(current, total):
        downloaded[0] = current

    progress_task = asyncio.create_task(update_progress(
        smsg, lambda: downloaded[0], filesize or 1, start_time, "📥 Downloading", filename or "File"
    ))

    try:
        file_path = await user.download_media(msg, file_name="downloads/", progress=download_cb)
    except Exception as e:
        progress_task.cancel()
        await smsg.edit(f"❌ Download error: {e}")
        return

    progress_task.cancel()
    if not file_path:
        await smsg.edit("❌ Download failed.")
        return

    await smsg.edit("📤 Uploading...")
    uploaded = [0]
    start_upload = time.time()

    async def upload_cb(current, total):
        uploaded[0] = current

    upload_task = asyncio.create_task(update_progress(
        smsg, lambda: uploaded[0], os.path.getsize(file_path), start_upload, "📤 Uploading", os.path.basename(file_path)
    ))

    try:
        send_func = {
            "Document": bot.send_document,
            "Video": bot.send_video,
            "Audio": bot.send_audio,
            "Photo": bot.send_photo,
            "Voice": bot.send_voice,
            "Animation": bot.send_animation,
        }.get(msg_type)

        if send_func:
            await send_func(
                DB_CHANNEL,
                file_path,
                caption=(msg.caption or None),
                caption_entities=getattr(msg, "caption_entities", None),
                reply_markup=markup,
                reply_to_message_id=reply_to.id if reply_to else None
            )
        else:
            await smsg.edit("❌ Unsupported media type.")
            return
    except Exception as e:
        await smsg.edit(f"❌ Upload error: {e}")
    else:
        await smsg.delete()
    finally:
        upload_task.cancel()
        try:
            os.remove(file_path)
        except:
            pass
