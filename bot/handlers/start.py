from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.keyboards import main_menu, language_choice
from bot.locales import get_text
import aiosqlite
import os

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, lang):
    await message.answer(get_text(lang, 'start'), reply_markup=main_menu(lang))
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, language) VALUES (?, ?)", (message.from_user.id, lang))
        await db.commit()

@router.message(F.text.in_({"🌐 Сменить язык", "🌐 Change language", "🌐 Schimbă limba"}))
async def change_lang(message: Message, lang):
    await message.answer(get_text(lang, 'choose_lang'), reply_markup=language_choice())

@router.callback_query(F.data.startswith("set_lang_"))
async def set_lang(callback: Message, lang):
    new_lang = callback.data.split("_")[2]
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (new_lang, callback.from_user.id))
        await db.commit()
    await callback.message.edit_text(get_text(new_lang, 'lang_changed'))
    await callback.message.answer(get_text(new_lang, 'start'), reply_markup=main_menu(new_lang))
    await callback.answer()
