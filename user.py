# -*- coding: utf-8 -*-
"""Основной сценарий: /start -> квиз 8 вопросов -> результат -> приём -> оффер -> запись."""
import asyncio
import json
import logging

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import content
import database as db
import keyboards as kb
from scoring import compute_result
from states import QuizStates
from config import ADMIN_CHAT_ID

logger = logging.getLogger(__name__)
router = Router()


def _user_display(message_from_user) -> tuple[str, str]:
    username = message_from_user.username or ""
    full_name = message_from_user.full_name or ""
    return username, full_name


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    username, full_name = _user_display(message.from_user)
    db.upsert_user(message.chat.id, username, full_name)
    await message.answer(content.START_TEXT, reply_markup=kb.start_kb())


@router.callback_query(F.data == "start_quiz")
async def cb_start_quiz(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(QuizStates.in_quiz)
    await state.update_data(question_index=0, answers=[])
    await callback.message.answer(
        content.QUESTIONS[0]["text"], reply_markup=kb.question_kb(0)
    )


@router.callback_query(F.data.startswith("ans:"))
async def cb_answer(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()

    current = await state.get_data()
    current_index = current.get("question_index")
    answers = current.get("answers", [])

    try:
        _, q_index_str, choice_str = callback.data.split(":")
        q_index = int(q_index_str)
        choice = int(choice_str)
    except (ValueError, IndexError):
        return

    # Защита от нажатия кнопок на уже пройденном вопросе (старая клавиатура)
    if current_index is None or q_index != current_index:
        return

    # Убираем клавиатуру у отвеченного вопроса, чтобы нельзя было нажать дважды
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    answers = answers + [choice]
    next_index = q_index + 1

    if next_index < len(content.QUESTIONS):
        await state.update_data(question_index=next_index, answers=answers)
        await callback.message.answer(
            content.QUESTIONS[next_index]["text"],
            reply_markup=kb.question_kb(next_index),
        )
        return

    # Это был 8-й вопрос - считаем результат
    await state.clear()
    result = compute_result(answers)
    db.save_quiz_result(callback.message.chat.id, answers, result.result_type, result.patterns)

    await callback.message.answer(content.PRE_RESULT_TEXT)
    await asyncio.sleep(content.PRE_RESULT_PAUSE_SECONDS)

    if result.result_type == "single":
        pattern = result.patterns[0]
        await callback.message.answer(content.RESULT_TEXTS[pattern], reply_markup=kb.result_kb())
    else:
        first, second = result.patterns
        text = (
            f"{content.MIXED_RESULT_INTRO}\n\n"
            f"{content.RESULT_TEXTS[first]}\n\n"
            f"{content.MIXED_RESULT_BRIDGE}\n\n"
            f"{content.RESULT_TEXTS[second]}\n\n"
            f"{content.MIXED_RESULT_OUTRO}"
        )
        await callback.message.answer(text, reply_markup=kb.result_kb())


@router.callback_query(F.data == "show_technique")
async def cb_show_technique(callback: CallbackQuery):
    await callback.answer()
    user = db.get_user(callback.message.chat.id)
    if user is None or not user["result_patterns_json"]:
        # На случай прямого перехода без пройденного теста
        await callback.message.answer(content.START_TEXT, reply_markup=kb.start_kb())
        return

    patterns = json.loads(user["result_patterns_json"])
    technique_pattern = patterns[0]  # для mixed patterns[0] - паттерн, встретившийся раньше

    text = content.TECHNIQUE_TEXTS[technique_pattern]
    if technique_pattern in content.TECHNIQUES_WITHOUT_BUTTON:
        # После приёма 5 кнопки нет - сразу переходим к офферу
        await callback.message.answer(text)
        await _send_offer(callback.message)
    else:
        await callback.message.answer(text, reply_markup=kb.technique_next_kb())


@router.callback_query(F.data == "show_offer")
async def cb_show_offer(callback: CallbackQuery):
    await callback.answer()
    await _send_offer(callback.message)


async def _send_offer(message: Message):
    await message.answer(content.OFFER_INTRO_TEXT)
    await message.answer(content.OFFER_DETAILS_TEXT, reply_markup=kb.offer_kb())


@router.callback_query(F.data == "show_slots")
async def cb_show_slots(callback: CallbackQuery):
    await callback.answer()
    db.set_status(callback.message.chat.id, db.STATUS_REACHED_BOOKING)
    await _send_available_slots(callback.message)


async def _send_available_slots(message: Message, prefix_text: str | None = None):
    slots = db.list_available_slots()
    if not slots:
        await message.answer(content.NO_SLOTS_TEXT)
        return
    text = prefix_text or content.SLOTS_PROMPT_TEXT
    await message.answer(text, reply_markup=kb.slots_kb(slots))


@router.callback_query(F.data.startswith("book:"))
async def cb_book_slot(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    try:
        slot_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        return

    chat_id = callback.message.chat.id
    ok = db.book_slot(slot_id, chat_id)

    if not ok:
        await _send_available_slots(callback.message, prefix_text=content.SLOT_ALREADY_TAKEN_TEXT)
        return

    slot = db.get_slot(slot_id)
    slot_label = kb.format_slot_label(slot["slot_dt"]) if slot else "?"

    db.set_status(chat_id, db.STATUS_BOOKED)
    await callback.message.answer(content.BOOKING_CONFIRMED_TEXT.format(slot_dt=slot_label))

    username, full_name = _user_display(callback.from_user)
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                content.ADMIN_NEW_BOOKING_TEXT.format(
                    slot_dt=slot["slot_dt"] if slot else "?",
                    full_name=full_name or "без имени",
                    username=username or "нет username",
                    chat_id=chat_id,
                ),
            )
        except Exception:
            logger.exception("Не удалось отправить уведомление админу")
