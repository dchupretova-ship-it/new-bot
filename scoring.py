"""
Логика подсчёта результата теста, см. раздел 3 ТЗ.

Правила:
1. Считаем, сколько раз выбран каждый индекс (1-5) за 8 вопросов.
2. Индекс с максимальным числом ответов - основной результат ("single").
3. Если максимум делят два индекса - "смешанный тип": берём оба, но приём -
   для того индекса, который впервые встретился раньше по номеру вопроса.
4. Если максимум делят три и более индексов - берём те два индекса из них,
   которые встретились раньше всех остальных по номеру вопроса, и обрабатываем
   как обычный смешанный тип (тот же tie-break для приёма).
"""
from collections import Counter
from dataclasses import dataclass


@dataclass
class ScoreResult:
    result_type: str          # 'single' | 'mixed'
    patterns: list            # [pattern_index] или [first, second] в порядке первого появления
    technique_pattern: int    # индекс паттерна, для которого показываем приём


def compute_result(answers: list[int]) -> ScoreResult:
    if len(answers) != 8 or any(a not in (1, 2, 3, 4, 5) for a in answers):
        raise ValueError("answers должен быть списком из 8 значений 1..5")

    counts = Counter(answers)
    max_count = max(counts.values())
    candidates = [idx for idx in counts if counts[idx] == max_count]

    # индекс вопроса (0-based), на котором индекс паттерна впервые встретился
    first_occurrence = {idx: answers.index(idx) for idx in candidates}

    if len(candidates) == 1:
        pattern = candidates[0]
        return ScoreResult(result_type="single", patterns=[pattern], technique_pattern=pattern)

    # 2 и более кандидатов на максимум: берём двух самых ранних по первому появлению
    sorted_candidates = sorted(candidates, key=lambda idx: first_occurrence[idx])
    top_two = sorted_candidates[:2]
    return ScoreResult(
        result_type="mixed",
        patterns=top_two,          # top_two[0] встретился раньше top_two[1]
        technique_pattern=top_two[0],
    )
