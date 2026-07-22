import asyncio
import os
import aiosqlite

def send_broadcast(text_ru, text_en, text_ro, photo_url=None):
    from bot import bot          # берём bot из bot/__init__.py, без импорта main
    from bot.main import dp      # dp тоже нужен для event loop

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
