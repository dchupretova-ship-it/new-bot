# -*- coding: utf-8 -*-
from aiogram.fsm.state import State, StatesGroup


class QuizStates(StatesGroup):
    in_quiz = State()  # data: {"question_index": int, "answers": list[int]}
