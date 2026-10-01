# buddy_matching

员工双周伙伴匹配库：处理一个周期的完整输入快照，给出全局最优配对。

## 安装与测试

```bash
pip install -r requirements.txt   # 仅依赖 networkx
python -m pytest tests/
```

## 使用

```python
from buddy_matching import CycleSnapshot, Member, Rating, match_cycle, pair_score

members = (
    Member("a", "eng", frozenset({"hiking"}), utc_offset_minutes=480),
    Member("b", "ops", frozenset({"hiking", "go"}), utc_offset_minutes=540),
    Member("c", "ops", frozenset({"go"}), exited=True),  # 退出者不参与
)
ratings = (Rating(3, "a", "b", 5),)  # 历史评分，仅本周期之前生效
snapshot = CycleSnapshot(cycle=4, members=members, ratings=ratings)

pair_score(snapshot, members[0], members[1])  # 合法返回整数分数，否则 None
result = match_cycle(snapshot)                # result.pairs / result.unmatched
```

## 规则摘要

- 合法候选：双方均参与、部门不同、至少共享一个兴趣标签（字符串精确比较）、
  UTC 偏移绝对差 ≤ 180 分钟、双方均未屏蔽对方（屏蔽单向否决）。
- 分数：两个方向各自最近一次本周期之前评分之和 × 10 + 共享标签数；缺失方向按 3 星。
- 最优性（逐层字典序）：① 最大化配对数量；② 最大化已选配对最低分；③ 最大化总分。
  实现基于 networkx 最大权匹配：先定最大基数，再二分最低分门槛，最后在门槛子图上
  取最大基数 + 最大总权重匹配。
