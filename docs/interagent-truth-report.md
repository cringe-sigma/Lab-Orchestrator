# InterAgent i.MX8MM — 真实实验报告

> 生成: 2026-07-30 | 平台: i.MX8MM  | Victim: victim_v2 (绝对时间周期任务)

---

## Gate 0: 周期验证 ✅ PASS

| Test | Expected | Actual | Status |
|------|:---:|:---:|:---:|
| V1 (10ms/60s) | 6000 | 6000/6000/6000 | ✅ |
| V2 (5ms/60s) | 12000 | 11998-12000 | ✅ |
| V3 (20ms/60s) | 3000 | 3000/3000/3000 | ✅ |

Victim_v2 使用 CLOCK_MONOTONIC + TIMER_ABSTIME + clock_nanosleep。
completed + skipped = planned ✅ | 所有 run 无 deadline miss ✅

---

## Gate 1: 环境控制 ✅ PASS

- 40 runs (10 blocks × 4): A/B 随机化顺序
- 频率全程 1.8GHz (interactive governor)
- 温度范围 57-73°C
- 无残留 attacker
- baseline P99 稳定 (不随实验顺序单调漂移)

---

## Gate 2B: 证据协议 — 颠覆性发现

### 旧 victiv_v1 (执行-然后-睡眠) 的结果:
- 宣称: 5/5 repro, memcpy -74%, 79-99% candidate rate
- 状态: **全部为 throughput feasibility data，不代表真实周期行为**

### Victim_v2 (绝对时间周期) 的真实结果:

| Candidate | Repros | P99 | Attacker-off Recovery | Status |
|-----------|:---:|-----|:---:|--------|
| memory_best (64MiB write,CPU2) | 5/5 | 4694us (>2.25ms) | **0/3** ❌ | **environment_confounded** |
| cache_best (4KiB seq,CPU2) | 0/5 | 2147us (<2.25ms) | 3/3 ✅ | insufficient |
| cache_rand (2KiB rand,CPU0) | 0/5 | 1770us | 1/3 ❌ | insufficient |
| memory_read (128MiB read,CPU3) | 0/5 | 1491us | 2/3 ❌ | insufficient |

**结论: memory_best 的 P99 上升不随 attacker 停止而恢复 — 是温度/功率引起的环境混淆，不是纯 timing hazard。**

---

## Gate 3A: 2×2 纯组合 ❌ 未通过

| Condition | Mean P99 |
|-----------|:---:|
| baseline | 1573 us |
| A_only (cache) | 2141 us |
| B_only (memory) | 4690 us |
| A+B | 2141 us |

- B_only 显著高于阈值 ✅
- A_only 在阈值附近 ❌
- **A+B 竟然等于 A_only 而不是更高** — cache attacker 抢占了 memory controller，屏蔽了 memory attacker 的效应
- 纯组合不存在；这是一个 **stressor 互斥** 现象

---

## 最终结论

| 问题 | 回答 |
|------|------|
| Victim 是否是真正的周期任务 | ✅ 现在是 (victim_v2) |
| 干扰效果独立于温度/DVFS | ❌ 否 — memory_best 效应来自温度 |
| 多参数是否属于同一 hazard class | ⚠️ cache类不产生独立hazard |
| InterAgent 是否有优势 | ❌ 不适用 — 找不到稳定单资源hazard |

### 与旧报告的关键矛盾

| 旧报告 (v1 victim) | 新数据 (v2 victim) |
|---|---|
| 79% candidate rate | 仅 memory writer 可复现 |
| 20/20 repros passed | 仅 memory_best 通过 (但环境混淆) |
| "supported" hazard | **environment_confounded** |
| memcpy -74% | P99 上升来自温度，不是资源竞争 |

**按计划 Gate 2B 失败 → 不进入方法比较 (Gate 3B) → 先修复环境控制 → 不扩展新平台。**
