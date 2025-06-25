import enum
import shutil
from ast import arg
import asyncio
import re
from dataclasses import dataclass
import datetime as dt
import json

import pyrogram.errors
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaDocument

from config import env_vars, dbname
from img2cbz.core import fld2cbz
from img2pdf.core import fld2pdf, fld2thumb
from plugins import *
import os

from pyrogram import Client, filters
from typing import Dict, Tuple, List, TypedDict
from loguru import logger

from models.db import DB, ChapterFile, Subscription, LastChapter, MangaName, MangaOutput
from pagination import Pagination
from plugins.client import clean
from tools.aqueue import AQueue
from tools.flood import retry_on_flood

# Global dictionaries
mangas: Dict[str, MangaCard] = dict()
chapters: Dict[str, MangaChapter] = dict()
pdfs: Dict[str, str] = dict()
paginations: Dict[int, Pagination] = dict()
queries: Dict[str, Tuple[MangaClient, str]] = dict()
full_pages: Dict[str, List[str]] = dict()
favourites: Dict[str, MangaCard] = dict()
language_query: Dict[str, Tuple[str, str]] = dict()
users_in_channel: Dict[int, dt.datetime] = dict()
locks: Dict[int, asyncio.Lock] = dict()
all_search: Dict[str, str] = dict()

# Plugin configurations
plugin_dicts: Dict[str, Dict[str, MangaClient]] = {
    "🇬🇧 EN": {
        "MangaDex": MangaDexClient(),
        "Mgeko": MgekoClient(),
        "MangaKakalot": MangaKakalotClient(),
        "Manganelo": ManganeloClient(),
        "Manganato": ManganatoClient(),
        "MangaSee": MangaSeeClient(),
        "MangaBuddy": MangaBuddyClient(),
        "AsuraScans": AsuraScansClient(),
        "NineManga": NineMangaClient(),        
        "LikeManga": LikeMangaClient(),
        "FlameComics": FlameComicsClient(),
        "MangaPark": MangaParkClient(),
        "ReaperScans": ReaperScansClient(),
        "ManhwaClan": ManhwaClanClient(),
    },
    "🇪🇸 ES": {
        "MangaDex": MangaDexClient(language=("es-la", "es")),
        "ManhuaKo": ManhuaKoClient(),
        "TMO": TMOClient(),
        "Mangatigre": MangatigreClient(),
        "NineManga": NineMangaClient(language='es'),
        "MangasIn": MangasInClient(),
    },
    "🔞 18+": {
        "Manga18fx": Manga18fxClient(),
        "MangaDistrict": MangaDistrictClient(),
        "OmgeaScans": OmgeaScansClient(),
    }
}

# Initialize cache and help message
cache_dir = "cache"
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)
with open("tools/help_message.txt", "r") as f:
    help_msg = f.read()

class OutputOptions(enum.IntEnum):
    PDF = 1
    CBZ = 2

    def __and__(self, other):
        return self.value & other

    def __xor__(self, other):
        return self.value ^ other

    def __or__(self, other):
        return self.value | other

# Plugin initialization
disabled = []
plugins = dict()
for lang, plugin_dict in plugin_dicts.items():
    for name, plugin in plugin_dict.items():
        identifier = f'[{lang}] {name}'
        if identifier in disabled:
            continue
        plugins[identifier] = plugin

subsPaused = disabled + []

# Helper functions
def split_list(li):
    return [li[x: x + 2] for x in range(0, len(li), 2)]

def get_buttons_for_options(user_options: int):
    buttons = []
    for option in OutputOptions:
        checked = "✅" if option & user_options else "❌"
        text = f'{checked} {option.name}'
        buttons.append([InlineKeyboardButton(text, f"options_{option.value}")])
    return InlineKeyboardMarkup(buttons)

# Bot initialization
bot = Client(
    'bot',
    api_id=int(env_vars.get('API_ID')),
    api_hash=env_vars.get('API_HASH'),
    bot_token=env_vars.get('BOT_TOKEN'),
    max_concurrent_transmissions=3
)

pdf_queue = AQueue()

if dbname:
    DB(dbname)
else:
    DB()

# Message handlers
@bot.on_message(filters=~(filters.private & filters.incoming))
async def on_chat_or_channel_message(client: Client, message: Message):
    pass

@bot.on_message()
async def on_private_message(client: Client, message: Message):
    channel = env_vars.get('CHANNEL')
    if not channel:
        return message.continue_propagation()
    
    if in_channel_cached := users_in_channel.get(message.from_user.id):
        if dt.datetime.now() - in_channel_cached < dt.timedelta(days=1):
            return message.continue_propagation()
    
    try:
        if await client.get_chat_member(channel, message.from_user.id):
            users_in_channel[message.from_user.id] = dt.datetime.now()
            return message.continue_propagation()
    except pyrogram.errors.UsernameNotOccupied:
        logger.debug("Channel doesn't exist, continuing normally")
        return message.continue_propagation()
    except pyrogram.errors.ChatAdminRequired:
        logger.debug("Bot not admin of channel, continuing normally")
        return message.continue_propagation()
    except pyrogram.errors.UserNotParticipant:
        await message.reply(
            "Please join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Join', url=f't.me/{channel}')]]
            )
        )
    except Exception as e:
        logger.exception(e)

START_IMG = "https://files.catbox.moe/fvgszq.jpg"

START_BUTTONS = [
    [InlineKeyboardButton("SUPPORT" , url ="https://t.me/DemonsBots_Support")]]

@bot.on_message(filters=filters.command(['start']))
async def on_start(client: Client, message: Message):
    welcome_msg = """🌌 <b>Welcome to Manhwa Galactic Bot!</b> 🚀\n\n
Your personal gateway to manga, manhwa, and manhua — right on Telegram!\n\n
<b>✨ Features:</b>\n
• Search and download your favorite series\n
• Multiple language options and sources\n
• PDF/CBZ outputs with customization\n
• Chapter subscriptions and updates\n\n
<b>How to use:</b>\n
1. Type any manga/manhwa name\n
2. Follow the interactive buttons\n
3. Get your download instantly!\n\n
<b>Example:</b> <code>Solo Leveling</code>\n\n
Need help? Try /help or join our <a href='https://t.me/DemonsBots_Support'>support channel</a>.\n\n
<i>Happy reading! 🌠</i>"""

  
   
    await client.send_photo(chat_id = message.chat.id , photo = START_IMG , Caption = welcome_msg, parse_mode = 'html', reply_marup=InlineKeyboardMarkup(START_BUTTONS))

   #await message.reply(welcome_msg, parse_mode="html", disable_web_page_preview=True)

# [Include all other @bot.on_message handlers here...]

# Update and subscription management
async def update_mangas():
    """Check for new chapters and update subscribers"""
    logger.debug("Starting manga updates check")
    db = DB()
    
    # Get all data from DB
    subscriptions = await db.get_all(Subscription)
    last_chapters = await db.get_all(LastChapter)
    manga_names = await db.get_all(MangaName)

    # Build lookup dictionaries
    subs_dict = {}
    chapters_dict = {}
    url_client_dict = {}
    client_url_dict = {client: set() for client in plugins.values()}
    manga_dict = {}

    for sub in subscriptions:
        if sub.url not in subs_dict:
            subs_dict[sub.url] = []
        subs_dict[sub.url].append(sub.user_id)

    for lc in last_chapters:
        chapters_dict[lc.url] = lc

    for manga in manga_names:
        manga_dict[manga.url] = manga

    # Map URLs to clients
    for url in subs_dict:
        for ident, client in plugins.items():
            if ident in subsPaused:
                continue
            if await client.contains_url(url):
                url_client_dict[url] = client
                client_url_dict[client].add(url)

    # Check for updates
    for client, urls in client_url_dict.items():
        logger.debug(f'Checking updates for {client.name}')
        to_check = [chapters_dict[url] for url in urls if url in chapters_dict]
        
        if not to_check:
            continue
            
        try:
            updated, not_updated = await client.check_updated_urls(to_check)
        except Exception as e:
            logger.exception(f"Error checking updates: {e}")
            updated = []
            not_updated = list(urls)
            
        for url in not_updated:
            if url in url_client_dict:
                del url_client_dict[url]
                
        logger.debug(f'Found {len(updated)} updates')

    # Process updates
    updated_chapters = {}
    for url, client in url_client_dict.items():
        try:
            if url not in manga_dict:
                continue
                
            manga_name = manga_dict[url].name
            if url not in chapters_dict:
                # New subscription
                agen = client.iter_chapters(url, manga_name)
                last_chapter = await anext(agen)
                await db.add(LastChapter(url=url, chapter_url=last_chapter.url))
                await asyncio.sleep(10)
            else:
                # Check for new chapters
                last_chapter = chapters_dict[url]
                new_chapters = []
                counter = 0
                
                async for chapter in client.iter_chapters(url, manga_name):
                    if chapter.url == last_chapter.chapter_url:
                        break
                    new_chapters.append(chapter)
                    counter += 1
                    if counter == 20:  # Limit to 20 new chapters
                        break
                        
                if new_chapters:
                    last_chapter.chapter_url = new_chapters[0].url
                    await db.add(last_chapter)
                    updated_chapters[url] = list(reversed(new_chapters))
                    for chapter in new_chapters:
                        chapters[chapter.unique()] = chapter
                        
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.exception(f'Error processing {url}: {e}')

    # Notify subscribers
    blocked_users = set()
    for url, chapter_list in updated_chapters.items():
        for chapter in chapter_list:
            logger.info(f'New chapter: {chapter.manga.name} - {chapter.name}')
            for user_id in subs_dict[url]:
                if user_id in blocked_users:
                    continue
                    
                try:
                    await pdf_queue.put(chapter, int(user_id))
                    logger.debug(f"Added to queue for user {user_id}")
                except pyrogram.errors.UserIsBlocked:
                    logger.info(f'User {user_id} blocked the bot')
                    await remove_subscriptions(user_id)
                    blocked_users.add(user_id)
                except Exception as e:
                    logger.exception(f'Error notifying user {user_id}: {e}')

async def remove_subscriptions(user_id: str):
    """Remove all subscriptions for a user"""
    db = DB()
    await db.erase_user_subscriptions(user_id)

async def manga_updater():
    """Periodically check for manga updates"""
    check_interval = 5  # minutes
    while True:
        try:
            start_time = dt.datetime.now()
            await update_mangas()
            elapsed = dt.datetime.now() - start_time
            wait_time = max(check_interval * 60 - elapsed.total_seconds(), 0)
            logger.debug(f'Update completed in {elapsed}, next in {wait_time}s')
        except Exception as e:
            logger.exception(f'Update error: {e}')
            wait_time = 60  # Wait 1 minute on error
            
        await asyncio.sleep(wait_time)

async def chapter_creation(worker_id: int = 0):
    """Worker process for creating chapter files"""
    logger.debug(f"Worker {worker_id} started")
    while True:
        chapter, chat_id = await pdf_queue.get(worker_id)
        logger.debug(f"Worker {worker_id} processing {chapter.name} for {chat_id}")
        try:
            await send_manga_chapter(bot, chapter, chat_id)
        except Exception as e:
            logger.exception(f"Error sending chapter: {e}")
        finally:
            pdf_queue.release(chat_id)

# Main execution
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    
    # Start update checker
    loop.create_task(manga_updater())
    
    # Start worker processes
    for i in range(3):  # Number of parallel workers
        loop.create_task(chapter_creation(i))
        
    # Start the bot
    bot.run()
