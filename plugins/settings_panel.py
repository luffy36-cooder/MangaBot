# plugins/settings_panel.py

from bot import bot  # Import the bot instance
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@bot.on_message(filters.command("settings"))
async def settings_handler(client, message):
    user_id = message.from_user.id

    is_premium = check_if_premium(user_id)

    file_name = "Ch-{chap_num} {manga_name} @Manhwa_Galactic"
    caption = "{file_name}"
    quality = 90
    z_fill = 3
    name_length = 25

    setting_text = f"""
**⚙️ Settings for MangaBot**

📂 File Name: `{file_name}`
📝 Caption: `{caption}`
🔢 Name Length: `{name_length}`
📸 Quality: `{quality}`
0️⃣ Z-Fill: `{z_fill}`
🖼️ Thumbnail: *None*
📤 Dump Channel: *None*
🖼️ First Banner: *None*
🖼️ Last Banner: *None*
🔗 First Banner Link: *None*
🔗 Last Banner Link: *None*
🔐 Password: *None*

💎 Premium: {'✅ Valid' if is_premium else '❌ Not Valid'}
🗓️ Premium Till: 2025-07-14
"""

    buttons = [
        [
            InlineKeyboardButton("🧾 FILE NAME", callback_data="set_file_name"),
            InlineKeyboardButton("🖊️ CAPTION", callback_data="set_caption"),
        ],
        [
            InlineKeyboardButton("📏 NAME LENGTH", callback_data="set_name_length"),
            InlineKeyboardButton("📸 QUALITY", callback_data="set_quality"),
        ],
        [
            InlineKeyboardButton("0️⃣ Z-FILL", callback_data="set_zfill"),
            InlineKeyboardButton("🖼️ THUMBNAIL", callback_data="set_thumbnail"),
        ],
        [
            InlineKeyboardButton("🖼️ FIRST BANNER", callback_data="set_first_banner"),
            InlineKeyboardButton("🖼️ LAST BANNER", callback_data="set_last_banner"),
        ],
        [
            InlineKeyboardButton("🔗 FIRST BANNER LINK", callback_data="set_first_banner_link"),
            InlineKeyboardButton("🔗 LAST BANNER LINK", callback_data="set_last_banner_link"),
        ],
        [
            InlineKeyboardButton("📤 DUMP", callback_data="set_dump_channel"),
            InlineKeyboardButton("🔐 PASSWORD", callback_data="set_password"),
        ],
        [
            InlineKeyboardButton("💎 PREMIUM", callback_data="premium_panel"),
        ]
    ]

    await message.reply(setting_text, reply_markup=InlineKeyboardMarkup(buttons))


def check_if_premium(user_id):
    premium_users = [5137934602]  # Add your Telegram user ID or fetch from DB
    return user_id in premium_users
