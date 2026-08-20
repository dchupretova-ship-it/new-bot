# -*- coding: utf-8 -*-
"""Инлайн-клавиатуры бота."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import content


def start_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=content.START_BUTTON, callback_data="start_quiz")
    return kb.as_markup()


def question_kb(question_index: int) -> InlineKeyboardMarkup:
    """question_index: 0-based номер вопроса (0..7). Callback хранит и номер
    вопроса, и индекс варианта (1-5), чтобы хендлер не зависел от текущего
    состояния FSM для проверки, что ответ относится к текущему вопросу."""
    kb = InlineKeyboardBuilder()
    options = content.QUESTIONS[question_index]["options"]
    for i, option_text in enumerate(options, start=1):
        kb.button(text=option_text, callback_data=f"ans:{question_index}:{i}")
    kb.adjust(1)
    return kb.as_markup()


def result_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=content.RESULT_BUTTON, callback_data="show_technique")
    return kb.as_markup()


def technique_next_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=content.TECHNIQUE_NEXT_BUTTON, callback_data="show_offer")
    return kb.as_markup()


def offer_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=content.OFFER_BUTTON, callback_data="show_slots")
    return kb.as_markup()


def slots_kb(slots) -> InlineKeyboardMarkup:
    """slots: список sqlite3.Row с полями id, slot_dt."""
    kb = InlineKeyboardBuilder()
    for slot in slots:
        label = format_slot_label(slot["slot_dt"])
        kb.button(text=label, callback_data=f"book:{slot['id']}")
    kb.adjust(1)
    return kb.as_markup()


def format_slot_label(slot_dt: str) -> str:
    """slot_dt хранится как 'YYYY-MM-DD HH:MM' -> 'ДД.ММ, ЧЧ:ММ'."""
    try:
        date_part, time_part = slot_dt.split(" ")
        y, m, d = date_part.split("-")
        return f"{d}.{m}, {time_part}"
    except Exception:
        return slot_dt
