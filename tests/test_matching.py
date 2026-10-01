"""buddy_matching 自动化测试。"""
from __future__ import annotations

import itertools
import random

from buddy_matching import Member, Rating, match_cycle, pair_score


def brute_force_objectives(cycle, members, ratings):
    """测试专用穷举：枚举全部合法匹配，返回逐层最优的 (数量, 最低分, 总分)。"""
    active = [m for m in members if not m.exited]
    n = len(active)
    score = {}
    for i, j in itertools.combinations(range(n), 2):
        s = pair_score(active[i], active[j], cycle, ratings)
        if s is not None:
            score[(i, j)] = s

    best = (0, 0, 0)

    def rec(i, used, count, low, total):
        nonlocal best
        if i == n:
            candidate = (count, low if count else 0, total)
            if candidate > best:
                best = candidate
            return
        rec(i + 1, used, count, low, total)
        if i in used:
            return
        for j in range(i + 1, n):
            if j in used or (i, j) not in score:
                continue
            s = score[(i, j)]
            rec(i + 1, used | {i, j}, count + 1,
                s if count == 0 else min(low, s), total + s)

    rec(0, set(), 0, 0, 0)
    return best


def assert_matches_brute_force(cycle, members, ratings):
    result = match_cycle(cycle, members, ratings)
    expected = brute_force_objectives(cycle, members, ratings)
    actual = (result.pair_count, result.min_score, result.total_score)
    assert actual == expected, f"expected {expected}, got {actual}"

    by_id = {m.member_id: m for m in members}
    seen = set()
    for x, y in result.pairs:
        assert x not in seen and y not in seen, "成员重复配对"
        seen.update((x, y))
        assert pair_score(by_id[x], by_id[y], cycle, ratings) is not None
    active_ids = {m.member_id for m in members if not m.exited}
    assert set(result.unmatched) == active_ids - seen
    assert all(not by_id[m].exited for m in result.unmatched)


def member(mid, dept, tags=("t",), exited=False, blocked=(), offset=0):
    return Member(mid, dept, frozenset(tags), exited, frozenset(blocked), offset)


def test_odd_cycle():
    """奇数环：三角形最多配 1 对。"""
    ms = [member("a", "A"), member("b", "B"), member("c", "C")]
    assert_matches_brute_force(5, ms, [])
    result = match_cycle(5, ms, [])
    assert result.pair_count == 1
    assert len(result.unmatched) == 1


def test_one_way_block():
    """单向屏蔽即否决：a 屏蔽 b，a-b 非法，b-c 仍可配对。"""
    ms = [
        member("a", "A", blocked=("b",)),
        member("b", "B"),
        member("c", "C"),
    ]
    assert pair_score(ms[0], ms[1], 5, []) is None
    assert pair_score(ms[1], ms[2], 5, []) == 61
    assert_matches_brute_force(5, ms, [])
    result = match_cycle(5, ms, [])
    assert result.pairs == (("b", "c"),)
    assert result.unmatched == ("a",)


def test_offset_boundary_180():
    """180 分钟边界合法，181 分钟非法。"""
    a = member("a", "A", offset=0)
    b = member("b", "B", offset=180)
    c = member("c", "C", offset=181)
    assert pair_score(a, b, 5, []) == 61
    assert pair_score(a, c, 5, []) is None
    assert_matches_brute_force(5, [a, b, c], [])


def test_shuffled_history_latest_before_cycle_wins():
    """乱序历史：取本周期之前最近一次；本周期及未来不参与。"""
    a = member("a", "A")
    b = member("b", "B")
    ratings = [
        Rating(9, "a", "b", 1),   # 未来，忽略
        Rating(2, "b", "a", 2),
        Rating(4, "a", "b", 5),   # a->b 本周期前最近
        Rating(5, "a", "b", 1),   # 本周期，忽略
        Rating(1, "a", "b", 3),
        Rating(3, "b", "a", 4),   # b->a 本周期前最近
    ]
    assert pair_score(a, b, 5, ratings) == (5 + 4) * 10 + 1
    assert_matches_brute_force(5, [a, b], ratings)


def test_greedy_high_score_reduces_pair_count():
    """固定反例：路径 w-x-y-z，中间边 101 分，贪心选它会只剩 1 对。"""
    ms = [
        member("w", "A", tags=("t1",)),
        member("x", "B", tags=("t1",)),
        member("y", "A", tags=("t1", "t2")),
        member("z", "B", tags=("t2",)),
    ]
    ratings = [Rating(1, "x", "y", 5), Rating(1, "y", "x", 5)]  # x-y = 101
    result = match_cycle(5, ms, ratings)
    assert result.pair_count == 2
    assert result.total_score == 122  # w-x 61 + y-z 61
    assert set(map(frozenset, result.pairs)) == {frozenset("wx"), frozenset("yz")}
    assert_matches_brute_force(5, ms, ratings)


def test_disconnected_groups_global_optimum():
    """两组互无候选：第一组可选 {61,61} 或 {41,101}，第二组仅 {31}。

    全局最低分都是 31，逐层比较后应选总分更高的 {41,101,31}。
    """
    group1 = [
        member("p1", "A", tags=("t1",)),
        member("p2", "B", tags=("t1",)),
        member("p3", "B", tags=("t1",)),
        member("p4", "A", tags=("t1",)),
    ]
    group2 = [
        member("q1", "C", tags=("t2",)),
        member("q2", "D", tags=("t2",)),
    ]
    ratings = [
        Rating(1, "p1", "p3", 2), Rating(1, "p3", "p1", 2),  # p1-p3 = 41
        Rating(1, "p2", "p4", 5), Rating(1, "p4", "p2", 5),  # p2-p4 = 101
        Rating(1, "q1", "q2", 1), Rating(1, "q2", "q1", 2),  # q1-q2 = 31
    ]
    members = group1 + group2
    by_id = {m.member_id: m for m in members}

    assert pair_score(by_id["p1"], by_id["p2"], 5, ratings) == 61
    assert pair_score(by_id["p3"], by_id["p4"], 5, ratings) == 61
    assert pair_score(by_id["p1"], by_id["p3"], 5, ratings) == 41
    assert pair_score(by_id["p2"], by_id["p4"], 5, ratings) == 101
    assert pair_score(by_id["q1"], by_id["q2"], 5, ratings) == 31

    result = match_cycle(5, members, ratings)
    scores = sorted(
        pair_score(by_id[x], by_id[y], 5, ratings) for x, y in result.pairs
    )
    assert scores == [31, 41, 101]
    assert (result.pair_count, result.min_score, result.total_score) == (3, 31, 173)
    assert_matches_brute_force(5, members, ratings)


def test_no_pairs_objectives_are_zero():
    ms = [member("a", "A"), member("b", "A")]  # 同部门，无合法候选
    result = match_cycle(5, ms, [])
    assert (result.pair_count, result.min_score, result.total_score) == (0, 0, 0)
    assert set(result.unmatched) == {"a", "b"}


def test_excluded_members_not_in_unmatched():
    ms = [member("a", "A"), member("b", "B", exited=True)]
    result = match_cycle(5, ms, [])
    assert result.pairs == ()
    assert result.unmatched == ("a",)


def test_random_small_instances_against_brute_force():
    """至多 10 人的随机实例（含退出、屏蔽、偏移、乱序历史）核对三个目标值。"""
    rng = random.Random(20261002)
    for trial in range(60):
        n = rng.randint(0, 10)
        members = [
            member(
                f"m{i}",
                rng.choice(["A", "B", "C"]),
                tags=frozenset(t for t in "xyz" if rng.random() < 0.5),
                exited=rng.random() < 0.15,
                blocked=frozenset(f"m{j}" for j in range(n)
                                  if j != i and rng.random() < 0.1),
                offset=rng.choice([-180, -60, 0, 60, 180, 240]),
            )
            for i in range(n)
        ]
        cycle = rng.randint(2, 6)
        ratings = [
            Rating(rng.randint(0, 8), f"m{a}", f"m{b}", rng.randint(1, 5))
            for a in range(n) for b in range(n)
            if a != b and rng.random() < 0.3
        ]
        rng.shuffle(ratings)
        assert_matches_brute_force(cycle, members, ratings)
