from aiogram import BaseMiddleware
from aiogram.types import Update
import aiosqlite
import os

class LanguageMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = None
        if hasattr(event, 'from_user'):
            user = event.from_user
        if user:
            user_id = user.id
            async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
                cursor = await db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                if row:
                    lang = row[0]
                else:
                    lang = user.language_code if user.language_code in ('ru', 'en', 'ro') else 'en'
                    await db.execute("INSERT OR REPLACE INTO users (user_id, language) VALUES (?, ?)", (user_id, lang))
                    await db.commit()
            data["lang"] = lang
        else:
            data["lang"] = 'en'
        return await handler(event, data)
