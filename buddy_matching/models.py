"""数据模型：一个周期的完整输入快照与结果类型。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Member:
    """成员快照。blocked 为单向屏蔽：a 屏蔽 b 即否决 (a, b) 配对。"""

    member_id: str
    department: str
    interests: frozenset[str] = field(default_factory=frozenset)
    exited: bool = False
    blocked: frozenset[str] = field(default_factory=frozenset)
    utc_offset_minutes: int = 0


@dataclass(frozen=True)
class Rating:
    """一条有向评分记录：rater 在 cycle 周期给 ratee 打 stars 星（1-5）。"""

    cycle: int
    rater: str
    ratee: str
    stars: int


@dataclass(frozen=True)
class CycleSnapshot:
    """一个周期的完整输入快照。"""

    cycle: int
    members: tuple[Member, ...]
    ratings: tuple[Rating, ...] = ()


@dataclass(frozen=True)
class Pair:
    """一对已配对成员及其分数。"""

    member_a: str
    member_b: str
    score: int


@dataclass(frozen=True)
class MatchResult:
    """匹配结果：互不重复的配对 + 未配对成员（退出者不在其列）。"""

    pairs: tuple[Pair, ...]
    unmatched: tuple[str, ...]
