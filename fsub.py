import json
import os
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.types import Message
from typing import List
from pyrogram.errors import UserNotParticipant

# Load AUTH_CHANNELS from config.json or environment
try:
    with open('config.json', 'r') as f:
        DATA = json.load(f)
except Exception as e:
    print(f"[ERROR] config.json read failed: {e}")
    DATA = {}

def getenv(var):
    return os.environ.get(var) or DATA.get(var)

AUTH_CHANNELS = getenv("AUTH_CHANNELS") or [-1002008497819]

# Ensure AUTH_CHANNELS is a list of ints
if isinstance(AUTH_CHANNELS, str):
    AUTH_CHANNELS = [int(AUTH_CHANNELS)]
elif isinstance(AUTH_CHANNELS, list):
    AUTH_CHANNELS = [int(x) for x in AUTH_CHANNELS]

async def get_fsub(bot: Client, message: Message) -> bool:
    tb = await bot.get_me()
    user_id = message.from_user.id
    not_joined_channels = []

    for channel_id in AUTH_CHANNELS:
        try:
            await bot.get_chat_member(channel_id, user_id)
        except UserNotParticipant:
            try:
                chat = await bot.get_chat(channel_id)
                invite_link = chat.invite_link or await bot.export_chat_invite_link(channel_id)
                not_joined_channels.append((chat.title, invite_link))
            except Exception as e:
                print(f"[ERROR] Could not fetch chat info for {channel_id}: {e}")
        except Exception as e:
            print(f"[ERROR] Checking membership failed for {channel_id}: {e}")

    if not_joined_channels:
        join_buttons = []
        for i in range(0, len(not_joined_channels), 2):
            row = []
            for j in range(2):
                if i + j < len(not_joined_channels):
                    title, link = not_joined_channels[i + j]
                    row.append(InlineKeyboardButton(f"{i + j + 1}. {title}", url=link))
            join_buttons.append(row)

        join_buttons.append([
            InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{tb.username}?start=start")
        ])

        await message.reply(
            f"**🎭 {message.from_user.mention}, As I see, you haven’t joined my channel yet.\nPlease join using the button(s) below.**",
            reply_markup=InlineKeyboardMarkup(join_buttons)
        )
        return False

    return True
