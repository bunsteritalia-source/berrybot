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
import aiosqlite

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running"

def ping_self():
    while True:
        time.sleep(600)  # каждые 10 минут
        try:
            url = os.getenv("RENDER_EXTERNAL_URL")
            if url:
                urllib.request.urlopen(url)
        except:
            pass

def send_broadcast(text_ru, text_en, text_ro, photo_url=None):
    async def _broadcast():
        async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
            cursor = await db.execute("SELECT user_id, language FROM users")
            users = await cursor.fetchall()
        for user_id, lang in users:
            try:
                if lang == 'ru':
                    txt = text_ru
                elif lang == 'ro':
                    txt = text_ro
                else:
                    txt = text_en
                if photo_url:
                    base_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
                    full_url = base_url + photo_url
                    await bot.send_photo(user_id, photo=full_url, caption=txt)
                else:
                    await bot.send_message(user_id, txt)
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"Broadcast error for {user_id}: {e}")
    loop = dp.loop if hasattr(dp, 'loop') else asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(_broadcast())
    else:
        loop.run_until_complete(_broadcast())

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
    flask_app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=ping_self).start()
    asyncio.run(main())
