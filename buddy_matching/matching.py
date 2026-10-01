"""match_cycle：按三层优先级求全局最优配对。

优先级（逐层最优，后级不牺牲前级）：
1. 最大化配对数量；
2. 最大化已选配对中的最低分；
3. 最大化已选配对的分数总和。
"""
from __future__ import annotations

import networkx as nx

from .models import CycleSnapshot, MatchResult, Pair
from .scoring import pair_score


def _build_graph(snapshot: CycleSnapshot) -> nx.Graph:
    """以参与成员为点、合法候选为边（权重为分数）构建图。"""
    graph = nx.Graph()
    members = [m for m in snapshot.members if not m.exited]
    graph.add_nodes_from(m.member_id for m in members)
    for i, member_a in enumerate(members):
        for member_b in members[i + 1 :]:
            score = pair_score(snapshot, member_a, member_b)
            if score is not None:
                graph.add_edge(
                    member_a.member_id, member_b.member_id, weight=score
                )
    return graph


def _max_cardinality(graph: nx.Graph) -> int:
    if graph.number_of_edges() == 0:
        return 0
    matching = nx.max_weight_matching(graph, maxcardinality=True)
    return len(matching)


def match_cycle(snapshot: CycleSnapshot) -> MatchResult:
    """返回互不重复的成员对和所有未配对成员（退出者不参与也不列出）。"""
    graph = _build_graph(snapshot)
    participants = set(graph.nodes)

    target_size = _max_cardinality(graph)
    if target_size == 0:
        return MatchResult(pairs=(), unmatched=tuple(sorted(participants)))

    # 第二层：二分最大的最低分门槛，使该门槛下仍存在 target_size 的匹配。
    thresholds = sorted({data["weight"] for _, _, data in graph.edges(data=True)})
    lo, hi = 0, len(thresholds) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        sub = graph.edge_subgraph(
            (u, v)
            for u, v, data in graph.edges(data=True)
            if data["weight"] >= thresholds[mid]
        )
        if _max_cardinality(sub) >= target_size:
            lo = mid
        else:
            hi = mid - 1
    min_score = thresholds[lo]

    # 第三层：在门槛子图上求最大基数 + 最大总权重匹配。
    feasible = graph.edge_subgraph(
        (u, v)
        for u, v, data in graph.edges(data=True)
        if data["weight"] >= min_score
    )
    best = nx.max_weight_matching(feasible, maxcardinality=True)

    pairs = tuple(
        Pair(
            member_a=u,
            member_b=v,
            score=graph.edges[u, v]["weight"],
        )
        for u, v in sorted(best)
    )
    matched = {member for edge in best for member in edge}
    unmatched = tuple(sorted(participants - matched))
    return MatchResult(pairs=pairs, unmatched=unmatched)
