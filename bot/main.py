import asyncio
import threading
import time
import os
import urllib.request
from flask import Flask
from bot import bot, dp
from bot.handlers import start, catalog, cart, order, admin
from bot.middlewares.language import LanguageMiddleware
from db import init_db

# Импортируем админское приложение (теперь без цикла)
from admin_site.app import app as admin_app

def ping_self():
    while True:
        time.sleep(600)
        try:
            url = os.getenv("RENDER_EXTERNAL_URL")
            if url:
                urllib.request.urlopen(url)
        except:
            pass

async def main():
    await init_db()
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(order.router)
    dp.include_router(admin.router)
    dp.loop = asyncio.get_event_loop()
    await dp.start_polling(bot)

def run_flask():
    port = int(os.getenv('PORT', 10000))
    admin_app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=ping_self).start()
    asyncio.run(main())
