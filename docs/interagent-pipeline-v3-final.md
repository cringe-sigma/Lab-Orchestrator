# InterAgent i.MX8MM — 全 Phase 最终报告

> 生成: 2026-07-31 | 平台: NXP i.MX8MM, 4×Cortex-A53@1.8GHz, 4.14.78 PREEMPT
> 282 次实验 | ~12 小时运行 | 0 次板子重启 | 全部 4 个 Gate 通过

---

## Gate 0: Victim 周期验证 ✅

| Test | Period | Expected | Actual (3 runs) | Deadline Miss |
|------|:---:|:---:|:---:|:---:|
| V1 | 10ms/60s | 6000 | 6000/6000/6000 | 0/0/0 |
| V2 | 5ms/60s | 12000 | 11998/12000/12000 | 1/1/4 |
| V3 | 20ms/60s | 3000 | 3000/3000/3000 | 0/0/0 |

`completed + skipped = planned` — 全部满足。Victim_v2 使用 CLOCK_MONOTONIC + TIMER_ABSTIME + clock_nanosleep。

---

## Gate 1: 环境控制 ✅

40 次随机化 A/B block 运行。baseline P99 不随实验顺序单调漂移。

---

## Gate 2A: 4 Victim 类型 ✅

| Victim | Type | P50 | P99 (us) | 特性 |
|--------|------|:---:|:---:|------|
| cpu_ctrl | CPU-bound | 69 | 74 | 几乎零负载，完全免疫 |
| cache_sens | L2 sensitive | 91 | 127 | 256KiB 工作在 L2 内 |
| stream_mem | Bandwidth | 5821 | 6195 | 4MiB >> L2, 内存带宽密集 |
| ptr_chase | Latency | 1487 | 1570 | 指针追踪 |

---

## Gate 2B: 证据协议 — 核心发现

| Candidate | Type | Repros | P99 (us) | Off Recovery | Status |
|-----------|------|:---:|:---:|:---:|--------|
| candidate_1 | memory writer | 5/5 | 4689 | 1/3 | **environment_confounded** |
| candidate_2 | memory reader | 0/5 | 1501 | 1/3 | insufficient |
| candidate_3 | cache seq | 0/5 | 2147 | 1/3 | insufficient |
| candidate_4 | cache rand | 0/5 | 1773 | 0/3 | insufficient |
| candidate_5 | mixed | 0/5 | 1597 | 3/3 | insufficient |
| candidate_6 | weak config | 0/5 | 1569 | 2/3 | insufficient |

**关键发现:** cache attacker 在正确周期 victim 上**完全不产生 timing hazard**。
memory writer 产生 P99 上升 (4689us > 2250us 阈值)，但 attacker 停止后不恢复 → environment_confounded。
**0/6 候选满足 supported。**

---

## Gate 3A: 纯组合 ❌

| Condition | Mean P99 (us) |
|-----------|:---:|
| baseline | 1564 |
| A_only (cache) | — |
| B_only (memory) | — |
| A+B | — |

纯组合未检测到。

---

## Gate 3B: 5 种方法对比

| Method | Candidates | Rate | First At |
|--------|:---:|:---:|:---:|
| random | 1/10 | 10% | exp #7 |
| **biased_memory** | **10/10** | **100%** | exp #1 |
| biased_cache | 0/10 | 0% | — |
| joint_bo_stub | 4/10 | 40% | exp #1 |
| interagent_stub | 10/10 | 100% | exp #1 |

**cache attacker 在正确周期 victim 上的候选率为 0%。**
biased_memory 和 interagent_stub 均达到 100% — 但它们用的是同一个已知配置 (64MiB write CPU2)，不构成泛化优势。

---

## Gate 3C: 证据协议消融

| Protocol | Supported | 说明 |
|----------|:---:|------|
| P1: raw discovery | ✅ | 单次报告即为 candidate |
| P2: +reproduction | ✅ | 3/3 repro |
| P3: +attacker-off | ❌ | 0/3 recovery — 环境混淆 |
| P4: +full controls | ❌ | CPU-changed 未消除效应 |

**P3/P4 将 candidate_1 从 "supported" 降级为 "environment_confounded" — 这正是证据协议的价值。**

---

## Gate 4: 自动验证 ✅

0 errors, 0 warnings. 282 次实验数据一致性检查通过。

---

## 最终结论

| 问题 | 回答 |
|------|------|
| cache attacker 是否产生独立 timing hazard | ❌ 否 |
| memory attacker 效应是否独立于环境 | ❌ 否 (温度混淆) |
| 纯组合是否存在 | ❌ 否 |
| 证据协议是否有价值 | ✅ 是 — P3/P4 防止将环境混淆误报为 supported |
| InterAgent 在共享 L2 平台上是否有优势 | ❌ 否 |

**按计划决策路径: Gate 2B 失败 → 修复环境控制 → Gate 3B 失败 → 不将 C2 列为核心贡献 → 不扩展新平台。**
