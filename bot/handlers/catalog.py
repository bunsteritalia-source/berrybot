from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from bot.keyboards import categories_kb, back_button
from bot.locales import get_text
import aiosqlite
import os
import json
from aiogram.types import InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.message(F.text.in_({"🍓 Каталог", "🍓 Catalog", "🍓 Catalog"}))
async def show_categories(message: Message, lang):
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories")
        categories = await cursor.fetchall()
    if not categories:
        await message.answer(get_text(lang, 'empty_category'))
        return
    await message.answer(get_text(lang, 'select_category'), reply_markup=categories_kb(categories, lang))

@router.callback_query(F.data.startswith("cat_"))
async def show_products(callback: CallbackQuery, lang):
    cat_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products WHERE category_id = ? AND is_active = 1", (cat_id,))
        products = await cursor.fetchall()
    if not products:
        await callback.message.edit_text(get_text(lang, 'empty_category'), reply_markup=back_button(lang, "back_to_categories"))
        return
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.button(text=p[f'name_{lang}'], callback_data=f"prod_{p['id']}_{cat_id}")
    builder.button(text=get_text(lang, 'back'), callback_data="back_to_categories")
    builder.adjust(1)
    await callback.message.edit_text(get_text(lang, 'select_category'), reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("prod_"))
async def show_product(callback: CallbackQuery, lang):
    _, prod_id, cat_id = callback.data.split("_")
    prod_id = int(prod_id)
    cat_id = int(cat_id)
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
        product = await cursor.fetchone()
        if not product:
            await callback.answer("Product not found")
            return
        variants = []
        if product['has_variants']:
            var_cursor = await db.execute("SELECT * FROM product_variants WHERE product_id = ?", (prod_id,))
            variants = await var_cursor.fetchall()
        markup = InlineKeyboardBuilder()
        if variants:
            for v in variants:
                # Имя варианта всегда есть (генерируется в админке)
                label = v[f'name_{lang}']
                markup.button(text=f"{label} - {v['price']} MDL", callback_data=f"addvar_{v['id']}_{cat_id}")
        else:
            markup.button(text=f"Добавить в корзину ({product['base_price']} MDL)", callback_data=f"add_{prod_id}_{cat_id}")
        markup.button(text=get_text(lang, 'back'), callback_data=f"back_to_cat_{cat_id}")
        markup.adjust(1)
    photos = json.loads(product['photos']) if product['photos'] else []
    caption = f"{product[f'name_{lang}']}\n{product[f'description_{lang}']}"
    base_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
    try:
        if photos:
            if len(photos) > 1:
                media = [InputMediaPhoto(media=base_url + photos[0], caption=caption)]
                for ph in photos[1:]:
                    media.append(InputMediaPhoto(media=base_url + ph))
                await callback.message.answer_media_group(media)
            else:
                await callback.message.answer_photo(photo=base_url + photos[0], caption=caption)
        else:
            await callback.message.answer(caption)
    except:
        await callback.message.answer(caption)
    await callback.message.answer(get_text(lang, 'product_count'), reply_markup=markup.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("addvar_"))
async def add_variant(callback: CallbackQuery, lang):
    _, variant_id, cat_id = callback.data.split("_")
    variant_id = int(variant_id)
    await add_to_cart_db(callback.from_user.id, variant_id=variant_id)
    await callback.answer(get_text(lang, 'add_to_cart'))
    await callback.message.answer(get_text(lang, 'add_to_cart'), reply_markup=back_button(lang, f"back_to_cat_{cat_id}"))

@router.callback_query(F.data.startswith("add_"))
async def add_product(callback: CallbackQuery, lang):
    _, prod_id, cat_id = callback.data.split("_")
    prod_id = int(prod_id)
    await add_to_cart_db(callback.from_user.id, product_id=prod_id)
    await callback.answer(get_text(lang, 'add_to_cart'))
    await callback.message.answer(get_text(lang, 'add_to_cart'), reply_markup=back_button(lang, f"back_to_cat_{cat_id}"))

async def add_to_cart_db(user_id, variant_id=None, product_id=None):
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        if variant_id:
            cur = await db.execute("SELECT product_id FROM product_variants WHERE id = ?", (variant_id,))
            row = await cur.fetchone()
            if not row:
                return
            prod_id = row[0]
            cur = await db.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ? AND variant_id = ?",
                                   (user_id, prod_id, variant_id))
            row = await cur.fetchone()
            if row:
                await db.execute("UPDATE cart SET quantity = quantity + 1 WHERE user_id = ? AND product_id = ? AND variant_id = ?",
                                 (user_id, prod_id, variant_id))
            else:
                await db.execute("INSERT INTO cart (user_id, product_id, variant_id, quantity) VALUES (?,?,?,1)",
                                 (user_id, prod_id, variant_id))
        elif product_id:
            cur = await db.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ? AND variant_id = 0",
                                   (user_id, product_id))
            row = await cur.fetchone()
            if row:
                await db.execute("UPDATE cart SET quantity = quantity + 1 WHERE user_id = ? AND product_id = ? AND variant_id = 0",
                                 (user_id, product_id))
            else:
                await db.execute("INSERT INTO cart (user_id, product_id, variant_id, quantity) VALUES (?,?,0,1)",
                                 (user_id, product_id))
        await db.commit()

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, lang):
    async with aiosqlite.connect(os.getenv("DB_PATH", "berry.db")) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM categories")
        categories = await cursor.fetchall()
    await callback.message.edit_text(get_text(lang, 'select_category'), reply_markup=categories_kb(categories, lang))
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_cat_"))
async def back_to_category(callback: CallbackQuery, lang):
    cat_id = int(callback.data.split("_")[-1])
    await show_products(callback, lang)
    await callback.answer()
