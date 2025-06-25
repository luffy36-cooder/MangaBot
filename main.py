import plugins.settings_panel  # ✅ this registers the @Client.on_message for /settings
import asyncio as aio
from bot import *  # this imports all handlers including your settings
# ❌ REMOVE: from tools.settings_panel import settings_handler

async def async_main():
    db = DB()
    await db.connect()
    await bot.start()
    aio.create_task(manga_updater())
    for i in range(10):
        aio.create_task(chapter_creation(i + 1))
    await aio.Event().wait()  # Keeps the bot running

if __name__ == '__main__':
    aio.run(async_main())
