"""pair_score：判断两名成员本周期能否配对，合法时返回整数分数。"""
from __future__ import annotations

from .models import CycleSnapshot, Member

MAX_OFFSET_DIFF_MINUTES = 180
DEFAULT_STARS = 3


def _latest_stars_before(
    snapshot: CycleSnapshot, rater_id: str, ratee_id: str
) -> int:
    """本周期之前 rater->ratee 方向最近一次评分，缺失按 3 星。"""
    best_cycle = -1
    best_stars = DEFAULT_STARS
    for rating in snapshot.ratings:
        if (
            rating.rater == rater_id
            and rating.ratee == ratee_id
            and rating.cycle < snapshot.cycle
            and rating.cycle > best_cycle
        ):
            best_cycle = rating.cycle
            best_stars = rating.stars
    return best_stars


def pair_score(
    snapshot: CycleSnapshot,
    member_a: Member,
    member_b: Member,
) -> int | None:
    """合法候选返回整数分数，否则返回 None。

    合法条件：双方均参与、部门不同、至少共享一个兴趣标签、
    UTC 偏移绝对差不超过 180 分钟、双方都没有屏蔽对方。
    分数 = 两个方向最近评分之和 * 10 + 共享标签数。
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
    if abs(member_a.utc_offset_minutes - member_b.utc_offset_minutes) > (
        MAX_OFFSET_DIFF_MINUTES
    ):
        return None
    if (
        member_b.member_id in member_a.blocked
        or member_a.member_id in member_b.blocked
    ):
        return None

    stars_ab = _latest_stars_before(
        snapshot, member_a.member_id, member_b.member_id
    )
    stars_ba = _latest_stars_before(
        snapshot, member_b.member_id, member_a.member_id
    )
    return (stars_ab + stars_ba) * 10 + len(shared)
