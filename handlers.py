import logging
import re
from datetime import timezone
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

import db
from keyboards import panel_keyboard

router = Router()
log = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Bratislava")
PANEL_KW = dict(
    parse_mode="HTML",
    link_preview_options=LinkPreviewOptions(is_disabled=True),
)

# кириллические двойники латинских букв -> латинские
CYR_TO_LAT = str.maketrans("АВЕКМНОРСТХ", "ABEKMHOPCTX")
ROOM_RE = re.compile(r"[A-Z]?\d{2,4}")


def normalize_room(text: str):
    """'a-305', 'А305', '312' -> 'A305', 'A305', '312'. Не похоже на комнату -> None."""
    text = re.sub(r"[\s\-]", "", text).upper().translate(CYR_TO_LAT)
    return text if ROOM_RE.fullmatch(text) else None


def fmt_time(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(TZ).strftime("%d.%m %H:%M")


def photo_link(chat_id, message_id):
    s = str(chat_id)
    if chat_id is None or message_id is None or not s.startswith("-100"):
        return None
    return f"https://t.me/c/{s[4:]}/{message_id}"


def panel_text() -> str:
    lines = ["🔑 <b>Ключи от кухни</b>", ""]
    for room in db.get_rooms():
        if room["borrowed_by"] is None:
            lines.append(f"{room['code']}: ✅ ключ дома")
        else:
            lines.append(
                f"{room['code']}: ❌ у комнаты {room['borrowed_by']} "
                f"с {fmt_time(room['since'])}"
            )

    history = db.last_history(5)
    if history:
        lines += ["", "Последние обмены:"]
        for h in history:
            returned = fmt_time(h["returned_at"]) if h["returned_at"] else "ещё не вернули"
            link = photo_link(h["photo_chat_id"], h["photo_message_id"])
            photo = f' (<a href="{link}">фото</a>)' if link else ""
            lines.append(
                f"{h['owner_room']} → {h['borrower_room']}: "
                f"{fmt_time(h['given_at'])} — {returned}{photo}"
            )
    return "\n".join(lines)


async def refresh_panel(bot: Bot):
    panel = db.get_panel()
    if panel is None:
        return
    try:
        await bot.edit_message_text(
            text=panel_text(),
            chat_id=panel["chat_id"],
            message_id=panel["message_id"],
            reply_markup=panel_keyboard(),
            **PANEL_KW,
        )
    except TelegramBadRequest as e:
        log.warning("Не удалось обновить панель: %s", e)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет! Твой Telegram ID: {message.from_user.id}")


@router.message(Command("panel"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_panel(message: Message, bot: Bot):
    if message.from_user is None or db.get_user(message.from_user.id) is None:
        return
    sent = await message.answer(
        panel_text(), reply_markup=panel_keyboard(), **PANEL_KW
    )
    db.set_panel(sent.chat.id, sent.message_id)
    try:
        await bot.pin_chat_message(
            sent.chat.id, sent.message_id, disable_notification=True
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        await message.answer(
            "Не смог закрепить панель: дайте боту права администратора "
            "с правом закреплять сообщения."
        )


@router.message(F.photo, F.caption, F.chat.type.in_({"group", "supergroup"}))
async def on_photo(message: Message, bot: Bot):
    if message.from_user is None:
        return
    user = db.get_user(message.from_user.id)
    if user is None:
        return

    guest_room = normalize_room(message.caption)
    if guest_room is None:
        return  # обычное фото с обычной подписью, не наше дело

    panel = db.get_panel()
    if panel is not None and panel["chat_id"] != message.chat.id:
        return

    owner_room = user["room"]
    if guest_room == owner_room:
        await message.reply("Нельзя отдать ключ собственной комнате.")
        return

    given_at = message.date.astimezone(timezone.utc).isoformat()
    ok = db.give_key(
        owner_room,
        guest_room,
        message.photo[-1].file_id,
        message.chat.id,
        message.message_id,
        given_at,
    )
    if not ok:
        await message.reply(f"Ключ {owner_room} уже выдан. Сначала его должны вернуть.")
        return

    await message.reply(
        f"Принято: ключ {owner_room} → комната {guest_room}, {fmt_time(given_at)}"
    )
    await refresh_panel(bot)


@router.callback_query(F.data == "return")
async def on_return(callback: CallbackQuery, bot: Bot):
    user = db.get_user(callback.from_user.id)
    if user is None:
        await callback.answer("Тебя нет в списке участников.", show_alert=True)
        return

    owner_room = user["room"]
    if not db.return_key(owner_room, db.now_iso()):
        await callback.answer(
            f"Ключ {owner_room} сейчас дома. "
            "Вернуть ключ может только комната, которой он принадлежит.",
            show_alert=True,
        )
        return

    await callback.answer("Ключ возвращён ✅")
    await refresh_panel(bot)