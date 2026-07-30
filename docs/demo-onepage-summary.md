# InterAgent i.MX8MM Demo — 一页总结

## 成功

在 i.MX8MM (4×Cortex-A53, 4.14.78 PREEMPT) 上，使用 periodic memory victim (CPU1, 10ms, 1MiB) + memory attacker (CPU2, 64MiB write) 组合，达成了以下闭环：

| 指标 | 数值 |
|------|------|
| 基线 max response time | 1.74 ms |
| 攻击下 max response time | 38.39 ms (**×24**) |
| 基线样本数/60s | 41,000 |
| 攻击下样本数/60s | 4,776 (**−88%**) |
| Repro pass rate | 20/20 (100%) |
| 搜索候选率 | 79% (38/48) |
| Benchmark memcpy 下降 | **−74%** |
| Benchmark List Traverse | **+433%** |
| Hazard status | **supported** |

跨核 cache/memory timing hazard 被系统性确认。CPU-bound 负载 (Dhrystone/Whetstone) 完全免疫。

## 失败 / 未决

- **精细归因 unresolved:** 共享 L2 + 统一 DRAM 控制器下，无法区分 cache capacity vs bandwidth 根因。按计划保留为 `fine_grained_attribution: unresolved`。
- **负对照温度残留:** memory attacker 64MiB write 使芯片从 57°C 升至 71°C，导致部分负对照 run 未完全恢复。
- **InterAgent 无优势:** 候选率 79%，随机搜索足够。需在 NUMA/big.LITTLE 平台才能体现两阶段 agent 价值。

## 下一步

按计划 §12 决策路径: **闭环成功 → 优先增加 Raspberry Pi 4 或 Pi 5**，验证:
1. 契约和 hazard record 能否跨平台复用作为搜索先验
2. InterAgent 两阶段策略在异构多核 (A72+A53) 上是否有优势
3. 此时再考虑 PREEMPT_RT 和 PolyRhythm-style baseline

---

*报告自动生成: 2026-07-30 | 数据源: IMX8MM 板载 | 计划一致性: 100%*
