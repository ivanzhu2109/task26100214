"""数据模型：一个匹配周期的完整输入快照与结果类型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Member:
    """成员快照。interests / blocked 按字符串精确比较。"""

    member_id: str
    department: str
    interests: frozenset[str] = field(default_factory=frozenset)
    exited: bool = False
    blocked: frozenset[str] = field(default_factory=frozenset)
    utc_offset_minutes: int = 0


@dataclass(frozen=True)
class Rating:
    """一条有向评价：rater 在 cycle 周期给 ratee 打 stars 星（1-5）。"""

    cycle: int
    rater: str
    ratee: str
    stars: int


@dataclass(frozen=True)
class MatchResult:
    """匹配结果：pairs 为互不重复的成员对，unmatched 为未配对成员（不含已退出者）。"""

    pairs: tuple[tuple[str, str], ...]
    unmatched: tuple[str, ...]
    pair_count: int
    min_score: Optional[int]
    total_score: int
