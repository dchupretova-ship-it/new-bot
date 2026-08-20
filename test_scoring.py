# -*- coding: utf-8 -*-
"""Юнит-тесты подсчёта результата (раздел 3 ТЗ) + проверка целостности контента."""
import content
from scoring import compute_result


def test_single_clear_winner():
    # индекс 3 встречается 4 раза - явный максимум
    answers = [3, 1, 3, 2, 3, 4, 5, 3]
    r = compute_result(answers)
    assert r.result_type == "single"
    assert r.patterns == [3]
    assert r.technique_pattern == 3


def test_mixed_two_way_tie_uses_earlier_first_occurrence():
    # индекс 1 первый раз на вопросе 1 (позиция 0), индекс 4 первый раз на вопросе 2 (позиция 1)
    # оба встречаются по 3 раза -> смешанный тип, приём - для индекса 1 (встретился раньше)
    answers = [1, 4, 1, 4, 1, 4, 2, 5]
    r = compute_result(answers)
    assert r.result_type == "mixed"
    assert r.patterns == [1, 4]
    assert r.technique_pattern == 1


def test_mixed_tie_order_depends_on_first_occurrence_not_value():
    # индекс 5 впервые на позиции 0, индекс 2 впервые на позиции 1 -> [5, 2], приём для 5
    answers = [5, 2, 5, 2, 5, 2, 1, 4]
    r = compute_result(answers)
    assert r.result_type == "mixed"
    assert r.patterns == [5, 2]
    assert r.technique_pattern == 5


def test_three_way_tie_takes_two_earliest():
    # индексы 1, 2, 3 встречаются по 2 раза каждый (максимум = 2).
    # первое появление: 1 -> позиция 0, 2 -> позиция 1, 3 -> позиция 2
    # берём два самых ранних: 1 и 2, приём для 1
    answers = [1, 2, 3, 1, 2, 3, 4, 5]
    r = compute_result(answers)
    assert r.result_type == "mixed"
    assert r.patterns == [1, 2]
    assert r.technique_pattern == 1


def test_invalid_length_raises():
    try:
        compute_result([1, 2, 3])
    except ValueError:
        pass
    else:
        raise AssertionError("должен был поднять ValueError на неполном списке ответов")


def test_invalid_value_raises():
    try:
        compute_result([1, 2, 3, 4, 5, 6, 1, 2])
    except ValueError:
        pass
    else:
        raise AssertionError("должен был поднять ValueError на значении вне 1..5")


def test_content_integrity():
    assert len(content.QUESTIONS) == 8, "должно быть ровно 8 вопросов"
    for i, q in enumerate(content.QUESTIONS):
        assert len(q["options"]) == 5, f"вопрос {i+1}: должно быть 5 вариантов"
        assert q["text"].strip(), f"вопрос {i+1}: пустой текст"

    for idx in range(1, 6):
        assert idx in content.RESULT_TEXTS, f"нет текста результата для паттерна {idx}"
        assert idx in content.TECHNIQUE_TEXTS, f"нет текста приёма для паттерна {idx}"
        assert content.RESULT_TEXTS[idx].strip()
        assert content.TECHNIQUE_TEXTS[idx].strip()

    assert content.TECHNIQUES_WITHOUT_BUTTON == {5}, "по ТЗ кнопки нет только после приёма 5"


if __name__ == "__main__":
    tests = [
        test_single_clear_winner,
        test_mixed_two_way_tie_uses_earlier_first_occurrence,
        test_mixed_tie_order_depends_on_first_occurrence_not_value,
        test_three_way_tie_takes_two_earliest,
        test_invalid_length_raises,
        test_invalid_value_raises,
        test_content_integrity,
    ]
    for t in tests:
        t()
        print(f"OK  {t.__name__}")
    print("\nВсе тесты прошли.")
