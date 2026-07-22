from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.locales import get_text
from bot.keyboards import main_menu, back_button
import aiosqlite
import os

router = Router()

@router.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

@router.message(F.text.in_({"ℹ️ Информация", "ℹ️ Information", "ℹ️ Informații"}))
async def show_info(message: Message, lang):
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        cursor = await db.execute("SELECT key, value FROM settings WHERE key LIKE 'info_%' OR key IN ('site_url','facebook_url','instagram_url','tiktok_url')")
        settings = dict(await cursor.fetchall())
    text = f"{settings.get('info_text_' + lang, '')}\n\n"
    text += f"🌐 {settings.get('site_url', '')}\n"
    text += f"📘 {settings.get('facebook_url', '')}\n"
    text += f"📷 {settings.get('instagram_url', '')}\n"
    text += f"🎵 {settings.get('tiktok_url', '')}"
    image = settings.get('info_image', '')
    base_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
    if image:
        try:
            await message.answer_photo(photo=base_url + image, caption=text)
        except:
            await message.answer(text)
    else:
        await message.answer(text)
    await message.answer("Вы в главном меню.", reply_markup=main_menu(lang))
