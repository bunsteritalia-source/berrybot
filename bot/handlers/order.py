from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from bot.states import OrderStates
from bot.locales import get_text
from bot.keyboards import main_menu
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiosqlite
import os
from bot.main import bot  # для отправки уведомлений

router = Router()

@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext, lang):
    user_id = callback.from_user.id
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        cur = await db.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (user_id,))
        count = (await cur.fetchone())[0]
    if count == 0:
        await callback.answer(get_text(lang, 'cart_empty'), show_alert=True)
        return
    await callback.message.answer(get_text(lang, 'order_name'))
    await state.set_state(OrderStates.waiting_for_name)

@router.message(OrderStates.waiting_for_name)
async def name_entered(message: Message, state: FSMContext, lang):
    await state.update_data(name=message.text)
    await message.answer(get_text(lang, 'order_phone'))
    await state.set_state(OrderStates.waiting_for_phone)

@router.message(OrderStates.waiting_for_phone)
async def phone_entered(message: Message, state: FSMContext, lang):
    await state.update_data(phone=message.text)
    await message.answer(get_text(lang, 'order_username'))
    await state.set_state(OrderStates.waiting_for_username)

@router.message(OrderStates.waiting_for_username)
async def username_entered(message: Message, state: FSMContext, lang):
    username = message.text.strip()
    if not username:
        await message.answer("Username обязателен! Введите ваш Telegram username (без @):")
        return
    await state.update_data(username=username)
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=get_text(lang, 'delivery'))],
        [KeyboardButton(text=get_text(lang, 'pickup'))]
    ], resize_keyboard=True, one_time_keyboard=True)
    await message.answer(get_text(lang, 'order_delivery'), reply_markup=kb)
    await state.set_state(OrderStates.waiting_for_delivery)

@router.message(OrderStates.waiting_for_delivery)
async def delivery_entered(message: Message, state: FSMContext, lang):
    if message.text not in [get_text(lang, 'delivery'), get_text(lang, 'pickup')]:
        await message.answer("Пожалуйста, выберите способ получения кнопкой.")
        return
    await state.update_data(delivery=message.text)
    await message.answer(get_text(lang, 'order_comment'))
    await state.set_state(OrderStates.waiting_for_comment)

@router.message(OrderStates.waiting_for_comment)
async def comment_entered(message: Message, state: FSMContext, lang):
    await state.update_data(comment=message.text)
    data = await state.get_data()
    user_id = message.from_user.id
    total = 0
    items_text = ""
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT c.product_id, c.variant_id, c.quantity,
                   p.name_ru, p.name_en, p.name_ro, p.base_price,
                   v.name_ru as var_name_ru, v.name_en as var_name_en, v.name_ro as var_name_ro,
                   v.price as var_price
            FROM cart c
            JOIN products p ON c.product_id = p.id
            LEFT JOIN product_variants v ON c.variant_id = v.id AND c.variant_id != 0
            WHERE c.user_id = ?
        """, (user_id,))
        cart_items = await cur.fetchall()
        for item in cart_items:
            prod_name = item[f'name_{lang}']
            if item['variant_id'] and item['variant_id'] != 0:
                var_name = item[f'var_name_{lang}']
                price = item['var_price']
                name = f"{prod_name} ({var_name})"
            else:
                price = item['base_price']
                name = prod_name
            qty = item['quantity']
            subtotal = price * qty
            total += subtotal
            items_text += f"{name} x{qty} = {subtotal} MDL\n"

    text = f"{get_text(lang, 'confirm_order')}\n\n{items_text}\n{get_text(lang, 'total')}: {total} MDL\n"
    text += f"Имя: {data['name']}\nТелефон: {data['phone']}\nUsername: @{data['username']}\n"
    text += f"Способ: {data['delivery']}\nКомментарий: {data['comment']}"
    await state.update_data(total=total, items=items_text)
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, 'confirm_btn'), callback_data="confirm_order")
    builder.button(text=get_text(lang, 'cancel_btn'), callback_data="cancel_order")
    await message.answer(text, reply_markup=builder.as_markup())
    await state.set_state(OrderStates.confirm)

@router.callback_query(OrderStates.confirm, F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext, lang):
    data = await state.get_data()
    user_id = callback.from_user.id
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        await db.execute("""
            INSERT INTO orders (user_id, username, items, total_price, customer_name, phone, telegram_username, delivery_method, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, callback.from_user.username or '', data['items'], data['total'],
              data['name'], data['phone'], data['username'], data['delivery'], data['comment']))
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        order_id = (await cur.fetchone())[0]
    await notify_admins(order_id, data, user_id, callback.from_user.username)
    await callback.message.edit_text(get_text(lang, 'order_accepted'))
    await callback.message.answer(get_text(lang, 'start'), reply_markup=main_menu(lang))
    await state.clear()

@router.callback_query(OrderStates.confirm, F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext, lang):
    await callback.message.edit_text("Заказ отменён.")
    await callback.message.answer(get_text(lang, 'start'), reply_markup=main_menu(lang))
    await state.clear()

async def notify_admins(order_id, data, user_id, username):
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        cur = await db.execute("SELECT telegram_id FROM admins WHERE notify_orders = 1 AND telegram_id IS NOT NULL")
        admins = await cur.fetchall()
        if not admins:
            return
        text = f"🆕 Новый заказ №{order_id}\n"
        text += f"От: {data['name']} (@{data['username']})\n"
        text += f"Телефон: {data['phone']}\n"
        text += f"Способ: {data['delivery']}\n"
        text += f"Комментарий: {data['comment']}\n"
        text += f"Состав:\n{data['items']}\n"
        text += f"Итого: {data['total']} MDL"
        for admin in admins:
            try:
                await bot.send_message(admin[0], text)
            except:
                pass
