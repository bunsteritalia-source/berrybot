from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.locales import get_text
from bot.keyboards import main_menu
import os
from bot.main import backup_database, restore_database, MAIN_ADMIN_ID

router = Router()

@router.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

@router.message(Command("backup"))
async def cmd_backup(message: Message):
    if message.from_user.id != MAIN_ADMIN_ID:
        await message.answer("Только главный администратор может делать бэкап.")
        return
    await backup_database()
    await message.answer("📦 Бэкап отправлен в этот чат.")

@router.message(Command("restore"))
async def cmd_restore(message: Message):
    if message.from_user.id != MAIN_ADMIN_ID:
        await message.answer("Только главный администратор может восстанавливать базу.")
        return
    # Если команда пришла как ответ на документ
    if message.reply_to_message and message.reply_to_message.document:
        file_id = message.reply_to_message.document.file_id
        success = await restore_database(file_id)
        if success:
            await message.answer("✅ База данных восстановлена! Перезапустите бота для применения изменений (можно просто нажать /start).")
        else:
            await message.answer("❌ Не удалось восстановить базу.")
    else:
        await message.answer("ℹ️ Чтобы восстановить базу, ответьте этой командой на сообщение с файлом бэкапа (.db).")

@router.message(F.text.in_({"ℹ️ Информация", "ℹ️ Information", "ℹ️ Informații"}))
async def show_info(message: Message, lang):
    import aiosqlite
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
