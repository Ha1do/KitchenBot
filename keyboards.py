from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Отдать ключ", callback_data="give")
    builder.button(text="Вернули ключ", callback_data="return")
    builder.button(text="История", callback_data="history")
    builder.adjust(2, 1)
    return builder.as_markup()