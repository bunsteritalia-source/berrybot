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

from admin_site.app import app as admin_app

MAIN_ADMIN_ID = int(os.getenv('MAIN_ADMIN_ID', '7942408433'))

def ping_self():
    while True:
        time.sleep(600)
        try:
            url = os.getenv("RENDER_EXTERNAL_URL")
            if url:
                urllib.request.urlopen(url)
        except:
            pass

async def backup_database():
    try:
        db_path = os.path.join(os.getcwd(), os.getenv("DB_PATH", "berry.db"))
        if not os.path.exists(db_path):
            await bot.send_message(MAIN_ADMIN_ID, f"❌ Файл базы не найден: {db_path}")
            return
        with open(db_path, 'rb') as f:
            await bot.send_document(MAIN_ADMIN_ID, f, caption="🔄 Автоматический бэкап базы данных")
    except Exception as e:
        await bot.send_message(MAIN_ADMIN_ID, f"❌ Ошибка бэкапа: {e}")

async def restore_database(file_id):
    try:
        db_path = os.path.join(os.getcwd(), os.getenv("DB_PATH", "berry.db"))
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, db_path)
        return True
    except Exception as e:
        print(f"Restore failed: {e}")
        return False

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

    async def periodic_backup():
        while True:
            await asyncio.sleep(3600)  # каждый час
            await backup_database()

    asyncio.create_task(periodic_backup())

    await dp.start_polling(bot)

def run_flask():
    port = int(os.getenv('PORT', 10000))
    admin_app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=ping_self).start()
    asyncio.run(main())
