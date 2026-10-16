from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

import db
from keyboards import panel_keyboard

router = Router()


def panel_text() -> str:
    lines = ["🔑 Ключи от кухни", ""]
    for room in db.get_rooms():
        if room["borrowed_by"] is None:
            lines.append(f"Комната {room['code']}: ✅ ключ дома")
        else:
            lines.append(
                f"Комната {room['code']}: ❌ нет ключа "
                f"(у комнаты {room['borrowed_by']}, с {room['since']})"
            )
    return "\n".join(lines)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет! Твой Telegram ID: {message.from_user.id}")


@router.message(Command("panel"))
async def cmd_panel(message: Message):
    if db.get_user(message.from_user.id) is None:
        await message.answer("Тебя нет в списке участников.")
        return
    await message.answer(panel_text(), reply_markup=panel_keyboard())


@router.callback_query(F.data.in_({"give", "return", "history"}))
async def buttons_stub(callback: CallbackQuery):
    if db.get_user(callback.from_user.id) is None:
        await callback.answer("Тебя нет в списке участников.", show_alert=True)
        return
    await callback.answer("Эта кнопка пока не реализована", show_alert=True)