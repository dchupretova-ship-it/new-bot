# -*- coding: utf-8 -*-
"""
Админ-команды для управления слотами записи - вместо TidyCal/Calendly бот
ведёт расписание сам. Доступны только из чата с ADMIN_CHAT_ID.

/addslot 2026-08-25 14:00
    добавить одно окно

/addslots 2026-08-25 14:00, 2026-08-25 16:00, 2026-08-26 10:00
    добавить несколько окон сразу (через запятую)

/slots
    список всех окон (свободные и занятые)

/delslot 3
    удалить окно по id (можно удалить только свободное)

/pending
    пользователи, которые дошли до записи, но не забронировали слот
    больше 24 часов назад - для ручного follow-up
"""
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

import database as db
from config import ADMIN_CHAT_ID

router = Router()

DT_FORMAT = "%Y-%m-%d %H:%M"


def _parse_dt(raw: str) -> str | None:
    raw = raw.strip()
    try:
        parsed = datetime.strptime(raw, DT_FORMAT)
        return parsed.strftime(DT_FORMAT)
    except ValueError:
        return None


# Все хендлеры этого роутера работают только в чате админа
router.message.filter(F.chat.id == ADMIN_CHAT_ID)


@router.message(Command("addslot"))
async def cmd_addslot(message: Message):
    raw = message.text.partition(" ")[2].strip()
    parsed = _parse_dt(raw)
    if not parsed:
        await message.answer(
            "Формат: /addslot 2026-08-25 14:00\n"
            "(дата ГГГГ-ММ-ДД, время ЧЧ:ММ)"
        )
        return
    slot_id = db.add_slot(parsed)
    await message.answer(f"Добавила слот #{slot_id}: {parsed}")


@router.message(Command("addslots"))
async def cmd_addslots(message: Message):
    raw = message.text.partition(" ")[2].strip()
    if not raw:
        await message.answer(
            "Формат: /addslots 2026-08-25 14:00, 2026-08-25 16:00, 2026-08-26 10:00"
        )
        return

    chunks = [c.strip() for c in raw.split(",") if c.strip()]
    added, errors = [], []
    for chunk in chunks:
        parsed = _parse_dt(chunk)
        if parsed:
            slot_id = db.add_slot(parsed)
            added.append(f"#{slot_id} {parsed}")
        else:
            errors.append(chunk)

    lines = []
    if added:
        lines.append("Добавила:\n" + "\n".join(added))
    if errors:
        lines.append("Не разобрала формат:\n" + "\n".join(errors))
    await message.answer("\n\n".join(lines) if lines else "Ничего не добавлено.")


@router.message(Command("slots"))
async def cmd_slots(message: Message):
    slots = db.list_all_slots()
    if not slots:
        await message.answer("Слотов пока нет. Добавь через /addslot.")
        return
    lines = []
    for s in slots:
        status = "занят" if s["is_booked"] else "свободен"
        lines.append(f"#{s['id']} - {s['slot_dt']} - {status}")
    await message.answer("\n".join(lines))


@router.message(Command("delslot"))
async def cmd_delslot(message: Message):
    raw = message.text.partition(" ")[2].strip()
    if not raw.isdigit():
        await message.answer("Формат: /delslot 3 (id слота из /slots)")
        return
    ok = db.delete_slot(int(raw))
    if ok:
        await message.answer(f"Удалила слот #{raw}.")
    else:
        await message.answer("Не нашла свободный слот с таким id (занятые слоты не удаляются).")


@router.message(Command("pending"))
async def cmd_pending(message: Message):
    raw = message.text.partition(" ")[2].strip()
    hours = 24.0
    if raw:
        try:
            hours = float(raw)
        except ValueError:
            pass

    rows = db.list_pending_bookings(older_than_hours=hours)
    if not rows:
        await message.answer(f"Никого нет: все, кто дошёл до записи, уложились в {hours:.0f} ч.")
        return

    lines = [f"Дошли до записи и молчат больше {hours:.0f} ч.:\n"]
    for r in rows:
        uname = f"@{r['username']}" if r["username"] else "без username"
        lines.append(f"- {r['full_name'] or '?'} ({uname}), chat_id {r['chat_id']}, с {r['updated_at']}")
    await message.answer("\n".join(lines))
