"""match_cycle：求逐层最优（数量、最低分、总分）的匹配方案。"""
from __future__ import annotations

import sys
from functools import lru_cache
from typing import Iterable, Optional

from .models import MatchResult, Member, Rating
from .scoring import pair_score

_INF = sys.maxsize


def match_cycle(
    cycle: int,
    members: Iterable[Member],
    ratings: Iterable[Rating],
) -> MatchResult:
    """返回本周期逐层最优的匹配方案。

    优化优先级：1) 配对数量最大；2) 已选配对最低分最大；3) 分数总和最大。
    已退出成员不参与，也不列入未配对名单。
    """
    records = list(ratings)
    active = [m for m in members if not m.exited]
    n = len(active)

    scores: list[list[Optional[int]]] = [[None] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            score = pair_score(active[i], active[j], cycle, records)
            scores[i][j] = scores[j][i] = score

    @lru_cache(maxsize=None)
    def best(mask: int) -> tuple[int, int, int]:
        """mask 内最优的 (配对数, 最低分, 总分)。空匹配最低分视为 +inf。"""
        if mask == 0:
            return (0, _INF, 0)
        lowbit = mask & (-mask)
        i = lowbit.bit_length() - 1
        rest = mask ^ lowbit
        result = best(rest)
        sub = rest
        while sub:
            jbit = sub & (-sub)
            j = jbit.bit_length() - 1
            score = scores[i][j]
            if score is not None:
                cnt, low, total = best(rest ^ jbit)
                candidate = (cnt + 1, min(low, score), total + score)
                if candidate > result:
                    result = candidate
            sub ^= jbit
        return result

    full = (1 << n) - 1
    count, low, total = best(full)

    pairs: list[tuple[str, str]] = []
    mask = full
    while mask:
        target = best(mask)
        lowbit = mask & (-mask)
        i = lowbit.bit_length() - 1
        rest = mask ^ lowbit
        if best(rest) == target:
            mask = rest
            continue
        sub = rest
        while sub:
            jbit = sub & (-sub)
            j = jbit.bit_length() - 1
            score = scores[i][j]
            if score is not None:
                cnt, low2, total2 = best(rest ^ jbit)
                if (cnt + 1, min(low2, score), total2 + score) == target:
                    pairs.append((active[i].member_id, active[j].member_id))
                    mask = rest ^ jbit
                    break
            sub ^= jbit

    paired_ids = {mid for pair in pairs for mid in pair}
    unmatched = tuple(m.member_id for m in active if m.member_id not in paired_ids)
    return MatchResult(
        pairs=tuple(pairs),
        unmatched=unmatched,
        pair_count=count,
        min_score=low if count > 0 else 0,
        total_score=total,
    )
