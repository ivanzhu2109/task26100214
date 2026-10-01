"""match_cycle 的三层目标最优性测试（穷举核对）与跨群组场景。"""
from itertools import combinations

from buddy_matching import (
    CycleSnapshot,
    Member,
    Rating,
    match_cycle,
    pair_score,
)


def make_member(member_id, **overrides):
    defaults = dict(
        department=f"dept-{member_id}",
        interests=frozenset({"x"}),
        exited=False,
        blocked=frozenset(),
        utc_offset_minutes=0,
    )
    defaults.update(overrides)
    return Member(member_id, **defaults)


def brute_force_objectives(snapshot):
    """穷举所有匹配，返回 (配对数, 最低分, 总分) 的字典序最大值。"""
    members = [m for m in snapshot.members if not m.exited]
    edges = []
    for a, b in combinations(members, 2):
        score = pair_score(snapshot, a, b)
        if score is not None:
            edges.append((a.member_id, b.member_id, score))

    best = (0, 0, 0)

    def search(index, used, count, min_score, total):
        nonlocal best
        if index == len(edges):
            current = (count, min_score if count else 0, total)
            if current > best:
                best = current
            return
        u, v, score = edges[index]
        search(index + 1, used, count, min_score, total)
        if u not in used and v not in used:
            search(
                index + 1,
                used | {u, v},
                count + 1,
                min(min_score, score) if count else score,
                total + score,
            )

    search(0, frozenset(), 0, 0, 0)
    return best


def objectives_of(result):
    scores = [p.score for p in result.pairs]
    return (
        len(scores),
        min(scores) if scores else 0,
        sum(scores),
    )


def assert_globally_optimal(snapshot):
    result = match_cycle(snapshot)
    # 结构合法性：成员互不重复，未配对者均为参与成员，退出者不出现。
    matched = [m for p in result.pairs for m in (p.member_a, p.member_b)]
    assert len(matched) == len(set(matched))
    participants = {m.member_id for m in snapshot.members if not m.exited}
    assert set(matched) | set(result.unmatched) == participants
    assert set(matched) & set(result.unmatched) == set()
    # 三层目标与穷举结果一致。
    assert objectives_of(result) == brute_force_objectives(snapshot)
    return result


def sculpt(members, keep_edges, ratings=(), cycle=10):
    """全员默认两两合法，用单向屏蔽裁掉 keep_edges 之外的边。"""
    keep = {frozenset(e) for e in keep_edges}
    ids = [m.member_id for m in members]
    sculpted = []
    for m in members:
        blocked = set(m.blocked)
        for other in ids:
            if other != m.member_id and frozenset({m.member_id, other}) not in keep:
                blocked.add(other)
        sculpted.append(
            Member(
                m.member_id,
                m.department,
                m.interests,
                m.exited,
                frozenset(blocked),
                m.utc_offset_minutes,
            )
        )
    return CycleSnapshot(cycle, tuple(sculpted), tuple(ratings))


def test_odd_cycle_five_members():
    members = tuple(make_member(str(i)) for i in range(5))
    edges = [("0", "1"), ("1", "2"), ("2", "3"), ("3", "4"), ("4", "0")]
    ratings = (
        Rating(3, "0", "1", 5),
        Rating(1, "1", "0", 4),
        Rating(2, "2", "3", 1),
        Rating(4, "4", "0", 2),
    )
    snapshot = sculpt(members, edges, ratings)
    assert_globally_optimal(snapshot)


def test_one_way_block_and_offset_boundary():
    members = (
        make_member("a", utc_offset_minutes=0),
        make_member("b", utc_offset_minutes=180),
        make_member("c", utc_offset_minutes=-180),
        make_member("d", utc_offset_minutes=181),
        make_member("e", utc_offset_minutes=90, blocked=frozenset({"a"})),
        make_member("f", utc_offset_minutes=-90),
    )
    snapshot = CycleSnapshot(10, members)
    assert_globally_optimal(snapshot)


def test_shuffled_history_and_exited_member():
    members = tuple(make_member(str(i)) for i in range(6)) + (
        make_member("gone", exited=True),
    )
    ratings = (
        Rating(9, "0", "1", 5),
        Rating(2, "1", "0", 2),
        Rating(7, "2", "3", 4),
        Rating(1, "0", "1", 1),
        Rating(10, "3", "4", 5),  # 本周期记录不参与
        Rating(5, "4", "5", 3),
        Rating(8, "1", "2", 2),
    )
    snapshot = CycleSnapshot(10, members, ratings)
    result = assert_globally_optimal(snapshot)
    assert "gone" not in result.unmatched
    assert all("gone" not in (p.member_a, p.member_b) for p in result.pairs)


def test_high_score_local_choice_reduces_pair_count():
    # 路径 0-1-2-3：边权 101、102、102。单选最高分 102 只剩 1 对，
    # 最优为 {0-1, 2-3}：2 对、最低分 101、总分 203。
    members = (
        make_member("0"),
        make_member("1"),
        make_member("2", interests=frozenset({"x", "y"})),
        make_member("3", interests=frozenset({"x", "y"})),
    )
    edges = [("0", "1"), ("1", "2"), ("2", "3")]
    ratings = (
        Rating(1, "0", "1", 5),
        Rating(1, "1", "0", 5),
        Rating(1, "1", "2", 5),
        Rating(1, "2", "1", 5),
        Rating(1, "2", "3", 5),
        Rating(1, "3", "2", 5),
    )
    snapshot = sculpt(members, edges, ratings)
    result = assert_globally_optimal(snapshot)
    assert objectives_of(result) == (2, 101, 203)


def test_two_disconnected_groups_prefer_global_sum():
    # 第一组：a,d 同部门 dept-1；b,c 同部门 dept-2（部门可超过两个）。
    # 合法边 a-b(61)、c-d(61)、a-c(41)、b-d(101)，最大数量方案为
    # {61,61} 或 {41,101}。第二组 e-f 仅一对，分数 31。
    # 全局最低分恒为 31，故第三层比总分：应选 {41,101,31}。
    members = (
        make_member("a", department="dept-1"),
        make_member("b", department="dept-2"),
        make_member("c", department="dept-2"),
        make_member("d", department="dept-1"),
        make_member("e", department="dept-3", interests=frozenset({"z"})),
        make_member("f", department="dept-4", interests=frozenset({"z"})),
    )
    ratings = (
        Rating(1, "a", "c", 1),  # a-c: (1+3)*10+1 = 41
        Rating(1, "b", "d", 5),  # b-d: (5+5)*10+1 = 101
        Rating(1, "d", "b", 5),
        Rating(1, "e", "f", 1),  # e-f: (1+2)*10+1 = 31
        Rating(1, "f", "e", 2),
    )
    snapshot = CycleSnapshot(10, members, ratings)
    # 前置校验：第一组两种方案分数确实为 61/61 与 41/101。
    by_id = {m.member_id: m for m in members}
    assert pair_score(snapshot, by_id["a"], by_id["b"]) == 61
    assert pair_score(snapshot, by_id["c"], by_id["d"]) == 61
    assert pair_score(snapshot, by_id["a"], by_id["c"]) == 41
    assert pair_score(snapshot, by_id["b"], by_id["d"]) == 101
    assert pair_score(snapshot, by_id["e"], by_id["f"]) == 31

    result = assert_globally_optimal(snapshot)
    assert sorted(p.score for p in result.pairs) == [31, 41, 101]
    assert result.unmatched == ()
