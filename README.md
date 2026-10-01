# buddy_matching — 员工双周伙伴匹配库

处理一个周期的完整输入快照，给出逐层最优的伙伴配对方案。纯标准库实现，无运行时第三方依赖。

## 安装与测试

```bash
pip install -r requirements.txt   # 仅测试需要 pytest
python -m pytest tests/ -q
```

## 快速上手

```python
from buddy_matching import Member, Rating, match_cycle, pair_score

members = [
    Member("alice", "eng",  frozenset({"hiking", "go"}), utc_offset_minutes=480),
    Member("bob",   "ops",  frozenset({"hiking"}),       utc_offset_minutes=420),
    Member("carol", "eng",  frozenset({"go"}), exited=True),  # 已退出，不参与
]
ratings = [Rating(3, "alice", "bob", 5)]  # 第 3 周期 alice 给 bob 打 5 星

score = pair_score(members[0], members[1], cycle=4, ratings=ratings)
# -> 81: (5 + 3) * 10 + 1 个共享标签（缺失方向按 3 星）

result = match_cycle(cycle=4, members=members, ratings=ratings)
# result.pairs        -> (("alice", "bob"),)
# result.unmatched    -> ()           已退出成员不列入
# result.pair_count / result.min_score / result.total_score
```

## 规则摘要

- 合法候选：双方均未退出、部门不同、至少共享一个兴趣标签（字符串精确比较）、
  UTC 偏移绝对差 ≤ 180 分钟、双方均未屏蔽对方（屏蔽单向否决）。
- 配对分数：本周期之前两个方向各自最近一次评分（缺失按 3 星）之和 × 10 + 共享标签数；
  本周期及未来记录不参与。
- 匹配目标逐层最优：1) 配对数量最大；2) 已选配对最低分最大；3) 分数总和最大。
  无配对时最低分与总分均为 0；同目标值方案任选其一。

## 实现说明

`match_cycle` 使用子集动态规划（O(2ⁿ · n²)），直接按 `(数量, 最低分, 总分)`
元组字典序比较，天然保证逐层最优且为全局最优（不受群组划分影响）。
适合单周期几十人以内的快照规模。
