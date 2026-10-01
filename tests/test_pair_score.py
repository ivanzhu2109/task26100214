"""pair_score 的合法性与计分规则测试。"""
from buddy_matching import CycleSnapshot, Member, Rating, pair_score


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


def test_legal_pair_defaults_to_three_stars():
    a = make_member("a")
    b = make_member("b")
    snapshot = CycleSnapshot(10, (a, b))
    # (3+3)*10 + 1 个共享标签
    assert pair_score(snapshot, a, b) == 61


def test_exited_member_is_rejected():
    a = make_member("a", exited=True)
    b = make_member("b")
    snapshot = CycleSnapshot(10, (a, b))
    assert pair_score(snapshot, a, b) is None
    assert pair_score(snapshot, b, a) is None


def test_same_department_is_rejected():
    a = make_member("a", department="eng")
    b = make_member("b", department="eng")
    snapshot = CycleSnapshot(10, (a, b))
    assert pair_score(snapshot, a, b) is None


def test_no_shared_interest_is_rejected():
    a = make_member("a", interests=frozenset({"x"}))
    b = make_member("b", interests=frozenset({"y"}))
    snapshot = CycleSnapshot(10, (a, b))
    assert pair_score(snapshot, a, b) is None


def test_offset_boundary_180_minutes():
    a = make_member("a", utc_offset_minutes=0)
    b = make_member("b", utc_offset_minutes=180)
    c = make_member("c", utc_offset_minutes=181)
    d = make_member("d", utc_offset_minutes=-180)
    snapshot = CycleSnapshot(10, (a, b, c, d))
    assert pair_score(snapshot, a, b) is not None
    assert pair_score(snapshot, a, d) is not None
    assert pair_score(snapshot, a, c) is None


def test_one_way_block_vetoes_both_directions():
    a = make_member("a", blocked=frozenset({"b"}))
    b = make_member("b")
    snapshot = CycleSnapshot(10, (a, b))
    assert pair_score(snapshot, a, b) is None
    assert pair_score(snapshot, b, a) is None


def test_score_uses_latest_rating_per_direction_before_cycle():
    a = make_member("a", interests=frozenset({"x", "y"}))
    b = make_member("b", interests=frozenset({"y", "z"}))
    # 乱序历史；本周期 10 的记录不参与；a->b 取 cycle 9 的 5 星。
    ratings = (
        Rating(9, "a", "b", 5),
        Rating(4, "b", "a", 1),
        Rating(8, "a", "b", 2),
        Rating(6, "b", "a", 4),
        Rating(10, "a", "b", 1),
        Rating(2, "a", "b", 3),
    )
    snapshot = CycleSnapshot(10, (a, b), ratings)
    # a->b 最近为 cycle9 的 5 星；b->a 最近为 cycle6 的 4 星；共享标签 {y} 1 个。
    assert pair_score(snapshot, a, b) == (5 + 4) * 10 + 1


def test_missing_direction_defaults_to_three_stars():
    a = make_member("a")
    b = make_member("b")
    ratings = (Rating(1, "a", "b", 5),)
    snapshot = CycleSnapshot(10, (a, b), ratings)
    assert pair_score(snapshot, a, b) == (5 + 3) * 10 + 1
