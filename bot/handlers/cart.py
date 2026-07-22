from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.locales import get_text
from bot.keyboards import main_menu
import aiosqlite
import os

router = Router()

@router.message(F.text.in_({"🛒 Корзина", "🛒 Cart", "🛒 Coș"}))
async def view_cart_message(message: Message, lang):
    await show_cart(message, message.from_user.id, lang)

@router.callback_query(F.data.startswith("inc_"))
async def increase(callback: CallbackQuery, lang):
    _, prod_id, var_id = callback.data.split("_")
    prod_id = int(prod_id)
    var_id = int(var_id)
    user_id = callback.from_user.id
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        await db.execute("UPDATE cart SET quantity = quantity + 1 WHERE user_id = ? AND product_id = ? AND variant_id = ?",
                         (user_id, prod_id, var_id))
        await db.commit()
    await show_cart(callback, user_id, lang, edit=True)

@router.callback_query(F.data.startswith("dec_"))
async def decrease(callback: CallbackQuery, lang):
    _, prod_id, var_id = callback.data.split("_")
    prod_id = int(prod_id)
    var_id = int(var_id)
    user_id = callback.from_user.id
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        cur = await db.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ? AND variant_id = ?",
                               (user_id, prod_id, var_id))
        row = await cur.fetchone()
        if row and row[0] > 1:
            await db.execute("UPDATE cart SET quantity = quantity - 1 WHERE user_id = ? AND product_id = ? AND variant_id = ?",
                             (user_id, prod_id, var_id))
        else:
            await db.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ? AND variant_id = ?",
                             (user_id, prod_id, var_id))
        await db.commit()
    await show_cart(callback, user_id, lang, edit=True)

@router.callback_query(F.data.startswith("del_"))
async def delete_item(callback: CallbackQuery, lang):
    _, prod_id, var_id = callback.data.split("_")
    prod_id = int(prod_id)
    var_id = int(var_id)
    user_id = callback.from_user.id
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ? AND variant_id = ?",
                         (user_id, prod_id, var_id))
        await db.commit()
    await show_cart(callback, user_id, lang, edit=True)

async def show_cart(event, user_id, lang, edit=False):
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT c.product_id, c.variant_id, c.quantity,
                   p.name_ru, p.name_en, p.name_ro, p.base_price,
                   v.name_ru as var_name_ru, v.name_en as var_name_en, v.name_ro as var_name_ro,
                   v.price as var_price
            FROM cart c
            JOIN products p ON c.product_id = p.id
            LEFT JOIN product_variants v ON c.variant_id = v.id AND c.variant_id != 0
            WHERE c.user_id = ?
        """, (user_id,))
        items = await cursor.fetchall()

    if not items:
        text = get_text(lang, 'cart_empty')
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
        else:
            await event.answer(text)
        return

    total = 0
    text = f"{get_text(lang, 'cart')}:\n\n"
    builder = InlineKeyboardBuilder()
    for item in items:
        prod_name = item[f'name_{lang}']
        qty = item['quantity']
        if item['variant_id'] and item['variant_id'] != 0:
            var_name = item[f'var_name_{lang}']
            price = item['var_price']
            name = f"{prod_name} ({var_name})"
        else:
            price = item['base_price']
            name = prod_name
        subtotal = price * qty
        total += subtotal
        text += f"{name} x{qty} = {subtotal} MDL\n"
        builder.button(text="➕", callback_data=f"inc_{item['product_id']}_{item['variant_id']}")
        builder.button(text="➖", callback_data=f"dec_{item['product_id']}_{item['variant_id']}")
        builder.button(text="❌", callback_data=f"del_{item['product_id']}_{item['variant_id']}")
    text += f"\n{get_text(lang, 'total')}: {total} MDL"
    builder.adjust(3)
    builder.row()
    builder.button(text=get_text(lang, 'checkout'), callback_data="checkout")
    builder.button(text=get_text(lang, 'back'), callback_data="back_to_main_menu")
    markup = builder.as_markup()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup)
    else:
        await event.answer(text, reply_markup=markup)

@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main(callback: CallbackQuery, lang):
    await callback.message.answer(get_text(lang, 'start'), reply_markup=main_menu(lang))
    await callback.answer()
