from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import KeyboardButton, InlineKeyboardButton
from bot.locales import get_text

def main_menu(lang):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text(lang, 'catalog')))
    builder.add(KeyboardButton(text=get_text(lang, 'cart')))
    builder.add(KeyboardButton(text=get_text(lang, 'info')))
    builder.add(KeyboardButton(text=get_text(lang, 'change_lang')))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def back_button(lang, callback_data):
    return InlineKeyboardBuilder().add(
        InlineKeyboardButton(text=get_text(lang, 'back'), callback_data=callback_data)
    ).as_markup()

def categories_kb(categories, lang):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat[f'name_{lang}'], callback_data=f"cat_{cat['id']}")
    builder.button(text=get_text(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def language_choice():
    builder = InlineKeyboardBuilder()
    builder.button(text="Русский", callback_data="set_lang_ru")
    builder.button(text="English", callback_data="set_lang_en")
    builder.button(text="Română", callback_data="set_lang_ro")
    builder.adjust(1)
    return builder.as_markup()
