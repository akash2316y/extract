import json
import os
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.types import Message
from typing import List, Union
from pyrogram.errors import UserNotParticipant, PeerIdInvalid

# config.json se ya environment se data lena
try:
    with open('config.json', 'r') as f:
        DATA = json.load(f)
except Exception as e:
    print(f"[ERROR] config.json read failed: {e}")
    DATA = {}

def getenv(var):
    return os.environ.get(var) or DATA.get(var)

AUTH_CHANNELS = getenv("AUTH_CHANNELS") or ["@UnknownBotz"]

# Sab channel strings ko sahi format me list banake use karo
if isinstance(AUTH_CHANNELS, str):
    AUTH_CHANNELS = [AUTH_CHANNELS]
elif isinstance(AUTH_CHANNELS, list):
    AUTH_CHANNELS = [str(x).strip() for x in AUTH_CHANNELS]

async def get_fsub(bot: Client, message: Message) -> bool:
    tb = await bot.get_me()
    user_id = message.from_user.id
    not_joined_channels = []

    for channel in AUTH_CHANNELS:
        try:
            await bot.get_chat_member(channel, user_id)
        except UserNotParticipant:
            try:
                chat = await bot.get_chat(channel)
                invite_link = chat.invite_link or await bot.export_chat_invite_link(chat.id)
                not_joined_channels.append((chat.title, invite_link))
            except Exception as e:
                print(f"[ERROR] Could not fetch chat info for {channel}: {e}")
        except PeerIdInvalid:
            print(f"[ERROR] Invalid peer ID: {channel} — Make sure bot is added to the channel.")
        except Exception as e:
            print(f"[ERROR] Checking membership failed for {channel}: {e}")

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
            f"**🎭 {message.from_user.mention}, lagta hai aap abhi tak channel join nahi kiye ho.\nNiche ke button se join karein.**",
            reply_markup=InlineKeyboardMarkup(join_buttons)
        )
        return False

    return True
