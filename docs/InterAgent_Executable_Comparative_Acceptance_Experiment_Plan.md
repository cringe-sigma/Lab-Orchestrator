# InterAgent 可执行、可对比、可验收实验计划

## 1. 计划目标

本计划首先在现有 i.MX8MM 上解决四个问题：

1. victim 是否真的是周期任务；
2. 干扰效果是否独立于温度、DVFS、残留进程和实验顺序；
3. 多个参数实例是否属于同一个 hazard class；
4. InterAgent 是否比 random、单体 BO 和独立 Agent 更高效地发现纯组合 hazard。

在单平台通过全部 Gate 之前，不增加 Pi、NUMA 或 big.LITTLE 平台，不使用平台数量代替方法有效性。

最终成功标准：

> 在预注册且不根据结果反向裁剪的搜索空间中，InterAgent 使用与所有基线相同的端到端预算，更低成本地发现并独立验证多个纯组合 hazard；证据协议能拒绝环境混淆候选，并将重复参数实例聚合为稳定 hazard classes。

---

## 2. 统一术语和数据口径

### 2.1 周期任务指标

每个 victim job 必须输出：

```text
run_id
job_id
planned_release_ns
actual_start_ns
finish_ns
execution_time_ns
response_time_ns
release_jitter_ns
deadline_ns
deadline_miss
overrun
skipped_release
```

统一定义：

\[
response\_time=finish-planned\_release
\]

\[
release\_jitter=actual\_start-planned\_release
\]

禁止将固定时间内完成的循环次数称为 periodic jobs，也禁止将 throughput reduction 称为 samples lost。

### 2.2 Hazard 阈值

只保留一个阈值：

\[
\delta=1.5\times median(P99_{baseline\ runs})
\]

阈值在正式 discovery 前冻结并写入：

```text
configs/locked_protocol.yaml
```

报告、搜索程序、confirmation 和 hazard record 必须读取同一个阈值文件，不允许分别硬编码 2.2 ms、2.52 ms 等不同值。

### 2.3 Candidate 与 Validated Hazard

```text
Candidate：一次discovery run的P99 > δ

Validated hazard：
  独立confirmation通过
  + attacker-off通过
  + 至少一个机制相关负对照通过
  + 环境检查通过
```

Candidate 不得直接写入最终 hazard class 数量。

### 2.4 效果量

主要效果量：

\[
d=\frac{P99_{test}-P99_{paired\ baseline}}{P99_{paired\ baseline}}
\]

辅助指标：P50、P95、P99.9、max、deadline-miss rate、skipped-release rate。

最终 hazard record 使用 confirmation 效果量，不使用 discovery 阶段最大值。

---

## 3. Phase 0：修复并验收周期 Victim

### 3.1 实现要求

- 使用 `CLOCK_MONOTONIC`；
- 使用 `clock_nanosleep(..., TIMER_ABSTIME, ...)`；
- release 时间为 `release_0 + job_id × period`；
- 不能用“执行完一次再相对 sleep”的方式产生周期；
- job 超过下一release时必须记录 overrun 或 skipped release；
- 每个 planned job 必须有明确状态，不能静默消失。

### 3.2 测试矩阵

| Test | Period | Duration | 预期 planned jobs |
|---|---:|---:|---:|
| V1 | 10 ms | 60 s | 6000 ± 1 |
| V2 | 5 ms | 60 s | 12000 ± 1 |
| V3 | 20 ms | 60 s | 3000 ± 1 |

每个测试执行 3 次，不运行 attacker。

### 3.3 输出

```text
results/victim_validation/V1_r1_jobs.csv
results/victim_validation/V1_r1_summary.json
...
```

Summary 至少包含：

```text
planned_jobs
completed_jobs
overruns
skipped_releases
deadline_misses
invalid_timestamps
duration_error_ms
```

### 3.4 验收条件 Gate 0

- [ ] 10 ms/60 s 的 planned jobs 为 6000 ± 1；
- [ ] `completed + skipped = planned`；
- [ ] 所有 `finish >= actual_start >= planned_release`，除明确记录的提前唤醒异常；
- [ ] 运行时长误差小于一个 period；
- [ ] CSV schema 固定；
- [ ] 报告不再出现 60秒约41,000个 periodic samples；
- [ ] 所有旧数据标记为 throughput feasibility data，不进入正式实时实验。

**Gate 0 未通过：停止后续全部实验。**

---

## 4. Phase 1：环境控制与随机化对照

### 4.1 环境记录

每次实验以 100–500 ms 周期采集：

```text
timestamp
cpu0..cpu3 frequency
temperature
governor
attacker_pid_alive
victim_pid_alive
loadavg
```

如果 sysfs 没有 thermal zone，必须记录实际温度来源；无法验证来源时，将 temperature 标记为 unavailable，不能在报告中使用温度数值。

### 4.2 CPU频率

优先使用固定频率或 `performance` governor。如果平台只能使用 `interactive`：

- 不宣称频率固定；
- 保存全程频率序列；
- 将频率作为 block/context 变量；
- 频率明显异常的 run 标记为 `env_confounded`。

### 4.3 进程清理

每次 run 结束后必须：

1. `wait` attacker PID；
2. 检查没有残留 attacker；
3. 等待系统达到预定义下一轮起始状态；
4. 保存 process snapshot。

### 4.4 随机化 block

定义：

```text
A = baseline/no attacker
B = representative memory attacker
```

执行 10 个 block，每个 block 随机选择：

```text
A-B-B-A
B-A-A-B
```

每个 run 使用相同 victim 参数和时长。

### 4.5 输出

```text
results/environment_blocks/block_plan.csv
results/environment_blocks/<run_id>_jobs.csv
results/environment_blocks/<run_id>_env.csv
results/environment_blocks/paired_analysis.csv
```

### 4.6 验收条件 Gate 1

- [ ] 所有 run 有完整频率/温度或明确 unavailable 标记；
- [ ] attacker-off run 不存在残留 attacker；
- [ ] baseline P99 不随实验顺序呈持续单调漂移；
- [ ] block 内 attacker-off P99 能恢复到该 block baseline 的预注册容差范围；
- [ ] 若不能恢复，相应 candidate 被标记为 `environment_confounded`；
- [ ] 报告不再使用“全部通过”概括同时包含失败负对照的数据。

推荐恢复判据：attacker-off 的 run-level P99 落入 baseline run-level P99 的 95% bootstrap interval，或相对差异低于预注册工程容差。具体容差在 pilot 后冻结。

**Gate 1 未通过：不运行搜索算法对比。**

---

## 5. Phase 2：建立正式 Victim 与 Stressor 空间

### 5.1 Victim集合

至少包含：

| Victim | 用途 |
|---|---|
| periodic CPU-oriented | 无效/弱效对照 |
| periodic cache-sensitive | cache-path敏感任务 |
| periodic streaming-memory | bandwidth敏感任务 |
| periodic pointer-chase | latency敏感任务 |

所有 victim 使用相同周期框架，但工作函数不同。

### 5.2 Stressor参数空间

#### Cache-like stressor

```text
working_set：小于L2 / 接近L2 / 2×L2 / 远大于L2
access：sequential / random
duty_cycle：0 / 25 / 50 / 75 / 100%
attacker_count：1 / 2
cpu：合法非victim核心
phase_offset：0 / 25 / 50 / 75% period
```

#### Memory-like stressor

```text
working_set：16 / 32 / 64 / 128 MiB
operation：read / write / copy
duty_cycle：0 / 25 / 50 / 75 / 100%
attacker_count：1 / 2
cpu：合法非victim核心
phase_offset：0 / 25 / 50 / 75% period
```

#### CPU control stressor

```text
integer / floating-point
duty_cycle：25 / 50 / 100%
```

### 5.3 搜索空间冻结原则

- 根据硬件合法能力和契约预先定义；
- 不根据目标 candidate rate 裁剪；
- 不以“使 random rate 达到20–40%”为设计目标；
- 正式实验后如实报告经验 hazard density；
- 任何新增或删除参数都形成新的 protocol version。

### 5.4 Pilot

使用分层随机抽样运行 30–50 个配置，仅用于：

- 检查参数可运行；
- 估计单次成本；
- 发现明显实现错误；
- 冻结最终空间。

Pilot 数据不进入正式方法比较。

### 5.5 验收条件 Gate 2A

- [ ] 至少4类victim全部使用正确周期框架；
- [ ] 所有参数范围写入版本化Contract；
- [ ] CPU control、attacker-off和低duty配置存在；
- [ ] Pilot没有大规模运行失败；
- [ ] 最终空间在正式比较前冻结；
- [ ] 不以candidate density作为通过/失败标准。

---

## 6. Phase 3：单资源 Hazard 的确认与证据状态

### 6.1 候选选择

从 pilot 或独立预实验选择：

- 2个稳定memory-like candidate；
- 2个cache-like candidate；
- 1个环境波动candidate；
- 1个CPU control candidate。

这些案例用于验证证据协议，不用于比较搜索效率。

### 6.2 每个候选执行

```text
5次独立confirmation
3次attacker-off
3次small-working-set或low-duty control
3次core-identity robustness control
连续环境监测
可用PMU采集
```

如果固定5次无法形成稳定区间，可继续运行到预注册最大预算；报告实际验证成本。

### 6.3 证据状态

```text
supported
contradicted
indistinguishable
unresolved
environment_confounded
budget_exhausted
```

### 6.4 验收条件 Gate 2B

- [ ] 至少一个candidate满足attacker-off恢复和机制相关负对照；
- [ ] 至少一个人为选择的混淆案例被标记为confounded，而不是supported；
- [ ] core relocation仅标记为robustness evidence，不伪装成topology negative control；
- [ ] 最终effect来自confirmation；
- [ ] cache与memory不可区分时输出`shared_cache_memory_path; fine_grained unresolved`；
- [ ] PMU缺失不阻塞现象确认，但限制机制结论。

---

## 7. Phase 4：Hazard实例聚合与Non-redundancy

### 7.1 Hazard signature

定义：

\[
\sigma(h)=(R,T,S,\Phi,Q,J)
\]

- \(R\)：支持的资源机制族；
- \(T\)：必要共享拓扑；
- \(S\)：必要调度条件；
- \(\Phi\)：有效相位类别；
- \(Q\)：效果类别，如稳定P99上涨、突发tail或deadline miss；
- \(J\)：负对照/干预响应签名。

working set、attacker CPU 等绝对参数不同，不自动构成新hazard class。

### 7.2 当前历史记录重分析

将原有：

```text
memory_e3
memory_e4
memory_e5
mem_w64_write_cpu2
```

重新聚合。预计：

- e3/e4/e5可能属于一个稳定shared-path class；
- mem_w64可能为独立的environment-confounded candidate，而不是supported class。

### 7.3 输出

```text
results/hazard_instances/*.yaml
results/hazard_classes/*.yaml
results/hazard_classes/instance_to_class.csv
```

### 7.4 验收条件 Gate 2C

- [ ] 每个instance映射到且仅映射到一个class或unresolved集合；
- [ ] class数量不等于配置文件数量；
- [ ] 聚合规则在方法比较前冻结；
- [ ] 报告不同相似度阈值下class数量敏感性；
- [ ] 所有搜索方法使用同一聚合器。

---

## 8. Phase 5：构造并验证纯组合 Hazard

### 8.1 先声明结论层级

第一阶段证明的是：

> 两个不同stressor配置之间存在纯组合timing interaction。

只有额外证据充分时，才提升为跨资源机制交互。不得因Agent名称直接称为cache×memory机制交互。

### 8.2 单项强度校准

对两个stressor分别扫描duty cycle和强度，寻找满足以下条件的配置区域：

\[
UCB(d_A)<\delta_d,qquad UCB(d_B)<\delta_d
\]

其中 \(\delta_d\) 为相对退化阈值，对应统一hazard阈值。

### 8.3 2×2随机化因子实验

每个候选组合执行：

| A | B | 含义 |
|---:|---:|---|
| 0 | 0 | baseline |
| 1 | 0 | A only |
| 0 | 1 | B only |
| 1 | 1 | A+B |

四个条件在每个block中随机排序。每个候选组合至少执行10个block或达到预注册置信标准。

### 8.4 纯组合判定

\[
UCB(d_A)<\delta_d
\]

\[
UCB(d_B)<\delta_d
\]

\[
LCB(d_{A,B})>\delta_d
\]

超加性使用预定义null model：

\[
\Gamma_{A,B}=d_{A,B}-d_A-d_B
\]

并报告 \(\Gamma\) 的bootstrap confidence interval。

### 8.5 组合案例集

至少覆盖：

- 不同victim；
- 不同phase offset；
- 不同stressor强度；
- 一个无交互负例；
- 一个明显组合正例；
- 若可行，一个纯组合正例。

### 8.6 验收条件 Gate 3A

- [ ] 2×2实验完整随机化；
- [ ] 单项和组合使用相同环境与victim上下文；
- [ ] 至少一个纯组合candidate通过独立confirmation；
- [ ] 至少一个无交互pair被正确判定为negative；
- [ ] 区分stressor interaction和resource-mechanism interaction；
- [ ] 只有一个案例时只能作为Motivation，不能支撑算法普遍性。

若无法找到纯组合实例，应重新评估论文是否继续以pure-combo discovery为中心，而不是通过修改阈值制造正例。

---

## 9. Phase 6：搜索方法公平对比

### 9.1 方法

必须运行：

1. Random；
2. Joint Bayesian Optimization；
3. Maximum-slowdown / PolyRhythm-style；
4. Independent Agents（无combo queue）；
5. Interaction-aware InterAgent；
6. 可选：InterAgent without interaction prior。

### 9.2 公平性

所有方法使用相同：

- victim集合；
- stressor实现；
-合法参数空间；
- 单次实验运行时长；
- 环境检查；
- candidate validator；
- hazard聚合器；
- 端到端预算。

InterAgent使用额外专家interaction prior时，必须同时报告无prior版本，分离知识收益与算法收益。

### 9.3 预算

预算以实际成本为主：

```text
total wall-clock
和
number of executed actions
```

所有动作计入：

```text
discovery
combination
confirmation
negative control
intervention
minimization
environment-invalid runs
```

### 9.4 重复

先使用5个种子做pilot比较，确认程序正确；正式锁定实验使用至少10个独立种子，具体数量根据pilot方差和可承受成本确定。

### 9.5 Primary metrics

1. cost-to-first-validated-pure-combo；
2. validated pure-combo classes under fixed budget；
3. total validated non-redundant classes under fixed budget；
4. confirmation yield；
5. false-candidate rate；
6. environment-confounded rate；
7. total wall-clock。

最大slowdown作为辅助指标，防止通过发现大量弱hazard规避PolyRhythm-style基线。

### 9.6 验收条件 Gate 3B

C2核心贡献只有同时满足下列条件才通过：

- [ ] Full InterAgent 在主要指标上优于最强基线，而不仅优于random；
- [ ] 优势在多个随机种子下稳定；
- [ ] bootstrap 95% interval 或其他预注册不确定性分析支持该差异；
- [ ] 优势计入confirmation和负对照成本后仍存在；
- [ ] Full InterAgent 不以明显牺牲最大slowdown为代价虚增弱hazard；
- [ ] 至少一部分优势来自interaction-aware设计，而非仅来自额外专家信息。

建议预注册工程意义阈值，例如相对最强基线减少至少20%的median cost-to-first-pure-combo；最终阈值应在正式实验前冻结，而不是在看到结果后选择。

如果Gate 3B失败：

- 不将multi-agent或interaction-aware discovery列为核心贡献；
- 保留ETIC和证据协议方向；
- 不通过增加平台掩盖单平台算法无优势。

---

## 10. Phase 7：证据协议对比与消融

### 10.1 对比配置

| 配置 | 内容 |
|---|---|
| P1 | discovery结果直接报告 |
| P2 | discovery + reproduction |
| P3 | reproduction + attacker-off |
| P4 | 完整协议：负对照+环境检查+结论限制 |

### 10.2 受控案例

至少包含：

- 稳定attacker-dependent hazard；
- attacker-off仍存在的环境混淆案例；
- 两个不同参数但同一hazard class的重复案例；
- 一个无法区分cache/memory的案例；
- 一个无交互pair；
- 一个纯组合pair。

### 10.3 指标

- false-supported rate；
- confounded detection rate；
- duplicate reduction；
- unresolved rate；
- validation cost；
- effect estimate shrinkage from discovery to confirmation。

### 10.4 验收条件 Gate 3C

- [ ] 完整协议比仅reproduction产生更少false-supported结果；
- [ ] mem_w64类残留效应不会被自动写成supported；
- [ ] e3/e4/e5类重复实例被聚合；
- [ ] 无法区分机制时输出unresolved而非错误细粒度标签；
- [ ] 报告验证成本，不把C3描述为免费附加功能。

---

## 11. Phase 8：报告与数据一致性自动验收

### 11.1 自动检查器

生成报告前运行：

```text
scripts/validate_results.py
```

检查：

- threshold来源唯一；
- summary count与原始CSV一致；
- planned/completed/skipped守恒；
- hazard effect来自confirmation；
- supported记录的必需负对照均通过；
- confounded记录不会出现在validated class计数中；
- 所有artifact路径存在；
- 所有对比方法预算一致；
- InterAgent表格不得使用“预期值”冒充实测值。

### 11.2 报告必须区分

```text
observed candidate
validated hazard instance
validated hazard class
confounded candidate
unresolved hypothesis
```

### 11.3 验收条件 Gate 4

- [ ] 自动检查器零error；
- [ ] warning全部在报告中解释；
- [ ] 不出现“闭环100%”但负对照失败的矛盾；
- [ ] 不使用Dhrystone 0.01 s支持“完全免疫”；
- [ ] Top candidates按预注册primary metric排序，不按max排序；
- [ ] 原始数据能够一键重建所有表格和图。

---

## 12. 推荐执行顺序

```text
Gate 0：周期语义
    ↓
Gate 1：环境与恢复
    ↓
Gate 2A：冻结合法搜索空间
    ↓
Gate 2B：单资源证据协议
    ↓
Gate 2C：实例聚合
    ↓
Gate 3A：纯组合案例集
    ↓
Gate 3B：搜索方法比较
    ↓
Gate 3C：证据协议消融
    ↓
Gate 4：报告一致性
```

任何 Gate 失败，先修复该层，不并行扩展新平台。

---

## 13. 建议目录结构

```text
interagent-demo/
├── configs/
│   ├── locked_protocol.yaml
│   ├── search_space_v1.yaml
│   └── evidence_rules_v1.yaml
├── contracts/
├── bindings/imx8mm/
├── src/
├── scripts/
│   ├── validate_victim.py
│   ├── run_randomized_blocks.py
│   ├── run_factorial_interaction.py
│   ├── run_search_comparison.py
│   ├── aggregate_hazards.py
│   ├── validate_results.py
│   └── generate_report.py
├── results/
│   ├── victim_validation/
│   ├── environment_blocks/
│   ├── pilot/
│   ├── discovery/
│   ├── confirmation/
│   ├── controls/
│   ├── interaction_factorial/
│   ├── method_comparison/
│   ├── hazard_instances/
│   └── hazard_classes/
└── reports/
```

---

## 14. 最终Go/No-Go决策表

| 结果 | 决策 |
|---|---|
| 周期语义不正确 | 停止，修复victim |
| attacker-off不能恢复 | 候选标记confounded，修复环境控制 |
| 多参数记录聚合为一个class | 正常，不虚增hazard数量 |
| 当前平台找不到纯组合案例 | 重新评估核心问题，再决定是否扩平台 |
| random/BO与InterAgent无差异 | C2不成立，不扩平台掩盖 |
| InterAgent只优于random | 方法贡献不足，继续强化基线或算法 |
| InterAgent计入验证成本后仍优于最强基线 | C2通过，可扩展第二平台 |
| 完整证据协议减少错误supported | C3通过 |
| Gate 0–4全部通过 | 开始真实应用和跨平台外部有效性实验 |

---

## 15. 当前立即执行的前三项

1. 修改 victim 为绝对时间周期任务，完成 Gate 0；
2. 实现频率/温度/进程时间序列采集，完成随机化 A/B block；
3. 将现有 e3/e4/e5 和 mem_w64 重新分类为 hazard instances、hazard class 与 confounded candidate。

在这三项完成前，不实现复杂交互图，也不新增硬件平台。
