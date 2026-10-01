"""pair_score：判断两名成员本周期能否配对，合法时返回整数分数。"""
from __future__ import annotations

from typing import Iterable, Optional

from .models import Member, Rating

MAX_OFFSET_DIFF_MINUTES = 180
DEFAULT_STARS = 3


def _latest_stars_before(
    ratings: Iterable[Rating], cycle: int, rater: str, ratee: str
) -> int:
    """取 cycle 之前 rater->ratee 最近一次评分，缺失按 3 星。"""
    best_cycle: Optional[int] = None
    best_stars = DEFAULT_STARS
    for record in ratings:
        if record.rater != rater or record.ratee != ratee:
            continue
        if record.cycle >= cycle:
            continue
        if best_cycle is None or record.cycle > best_cycle:
            best_cycle = record.cycle
            best_stars = record.stars
    return best_stars


def pair_score(
    member_a: Member,
    member_b: Member,
    cycle: int,
    ratings: Iterable[Rating],
) -> Optional[int]:
    """判断两名成员本周期能否配对。

    合法候选返回整数分数：(a->b 星 + b->a 星) * 10 + 共享标签数；
    否则返回 None。
    """
    if member_a.member_id == member_b.member_id:
        return None
    if member_a.exited or member_b.exited:
        return None
    if member_a.department == member_b.department:
        return None
    shared = member_a.interests & member_b.interests
    if not shared:
        return None
    if abs(member_a.utc_offset_minutes - member_b.utc_offset_minutes) > MAX_OFFSET_DIFF_MINUTES:
        return None
    if member_b.member_id in member_a.blocked or member_a.member_id in member_b.blocked:
        return None

    records = list(ratings)
    stars_ab = _latest_stars_before(records, cycle, member_a.member_id, member_b.member_id)
    stars_ba = _latest_stars_before(records, cycle, member_b.member_id, member_a.member_id)
    return (stars_ab + stars_ba) * 10 + len(shared)
