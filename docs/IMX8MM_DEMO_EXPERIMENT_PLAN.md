# i.MX8MM 单板 Demo 实验计划

## 1. 本轮实验目标

本轮只验证 i.MX8MM 单板上的最小闭环：

> 在固定实验预算内搜索 timing-hazard 候选，使用重复实验、attacker-off、环境控制和资源干预检查证据，再把结论写入结构化 hazard record，并用证据结果指导剩余预算。

本轮**不要求**证明跨平台迁移、跨 ISA 泛化，也不要求证明 InterAgent 优于所有搜索方法。

AI 辅助体不得以“必须找到干扰”为目标。没有稳定 hazard 也可以是有效结果，但必须能够区分：

- 当前配置下确实未观察到 hazard；
- 环境混淆导致无法判断；
- 测量协议或程序本身存在错误。

---

## 2. Demo 成功标准

### A：完整单板 PoC

同时满足：

1. 所有实验身份、baseline、victim 和配置可以追踪；
2. 检测器能发现人工注入的已知 timing violation；
3. 至少发现 1 个可重复的真实 cross-core hazard；
4. 至少有 1 个表面候选被证据协议正确降级；
5. 证据结论至少一次改变后续搜索选择；
6. 输出完整的结构化 hazard record 和原始证据。

### B：可信的单板负结果

满足数据质量要求，人工注入的阳性控制能够被检测，但所有真实 cross-core 候选经过验证后均为 `insufficient` 或 `environment_confounded`。

这种结果可以证明测量和证据管道基本可用，但不能证明搜索优势和资源归因能力。

### C：实验失败

出现以下任一情况：

- 不同 victim 共用同一个绝对时延阈值；
- candidate 找不到对应的 baseline 或原始 CSV；
- 汇总实验数和原始文件数不一致；
- 温度、频率或运行顺序缺失，无法判断环境影响；
- 人工注入的阳性控制无法被检测；
- 使用 stub 算法结果宣称搜索性能优势。

---

## 3. AI 辅助体的工作原则

1. 严格执行锁定配置，不得在实验中途静默修改阈值、victim 或搜索空间。
2. 每次运行生成唯一 `run_id`，所有原始文件均以该 ID 关联。
3. 先检查数据质量，再计算候选，不允许跳过失败运行。
4. 初筛命中只能称为 `candidate`，不能称为发现了 hazard。
5. 机制证据不足时输出 `ambiguous` 或 `insufficient`，不得强行选择 cache 或 memory。
6. AI 的每次搜索选择都要记录“选择了什么、为什么、使用了哪些已有证据”。
7. 如果达到停止条件，停止实验并报告原因，不要为了凑实验数量继续运行。

---

## 4. 每次运行必须收集的证据

### 4.1 实验身份

- `run_id`；
- 时间戳；
- Git commit；
- victim 名称、二进制哈希和全部参数；
- attacker 名称、二进制哈希和全部参数；
- victim/attacker CPU affinity；
- 实际执行命令；
- 搜索方法、campaign ID、随机种子和实验序号；
- condition：`baseline`、`attack`、`attacker_off`、`placebo` 或 `intervention`。

### 4.2 Victim 数据

- 每个 job 的 planned release、actual start、finish；
- execution time、response time、release jitter；
- deadline miss 和 skipped job；
- 每次运行的 P50、P95、P99、P99.9、最大值和 miss ratio。

### 4.3 Attacker 数据

- 实际运行时长；
- 完成的访问字节数或循环次数；
- 实际带宽或吞吐；
- 是否提前退出或发生错误。

### 4.4 环境数据

运行前、运行中每 1 秒、运行后记录：

- 所有可读 thermal zone；
- 每核实际频率；
- governor；
- throttling/cooling state；
- CPU 利用率；
- 内存使用量；
- context switch 和主要 IRQ 计数。

### 4.5 PMU/系统观测

在平台支持范围内至少收集：

- cycles、instructions；
- cache references、cache misses；
- L1/L2 refill 或最接近的可用事件；
- bus access 或最接近的内存流量代理；
- context switches、migrations、page faults。

事件不可用时写入 `unavailable`，不得填 0 冒充观测值。

---

## 5. 实验阶段

## E0：数据与程序自检

### AI 辅助体执行

1. 输出系统快照：内核、CPU、cache 拓扑、频率、governor、IRQ affinity 和 thermal zone。
2. 对四种 victim 和两种 attacker 各运行一次短测试。
3. 检查 job 数、时间单位、CSV 列、程序退出码和 attacker 吞吐。
4. 验证每个汇总结果都能回溯到唯一的原始文件。
5. 自动检查 `manifest rows = raw run directories = reported runs`。

### 通过条件

- 没有 victim 名称或配置错配；
- 没有缺失 CSV；
- planned jobs 与 completed/skipped 可以对账；
- attacker 确实产生访问流量；
- 时间单位全部统一为微秒。

任何一项失败，先修程序或汇总脚本，不进入正式实验。

---

## E1：Baseline 与环境稳定性

### AI 辅助体执行

对以下 victim 各运行 10 次、每次 60 秒：

- `cpu_ctrl`；
- `cache_sens`；
- `stream_mem`；
- `ptr_chase`。

运行顺序随机化。每次运行前等待温度回到预设起始区间；如果无法回到该区间，记录并停止当前 block。

### AI 辅助体汇总

对每个 victim 分别报告：

- 10 次运行的 P50/P99/max 分布；
- 第一次与最后一次 baseline 的差异；
- P99 与温度、频率的关系；
- deadline miss 和 skipped job；
- baseline 是否存在明显漂移。

### 判定规则

每个 victim 使用自己的 paired baseline，不再使用全局 2.25 ms 阈值。

候选初筛建议同时满足：

1. attack P99 相对 paired baseline 增加至少 20%；
2. P99 绝对增加至少 50 us，或出现新的 deadline miss；
3. attack 的结果超过 baseline 波动范围。

具体阈值必须在发现实验前锁定。若 baseline 明显随温度或时间漂移，先解决环境问题。

---

## E2：检测器正向和负向控制

### 正向控制

在 victim 中人工注入已知延迟，例如让固定比例的 job 增加已知的 2–3 ms 工作量或睡眠。运行 5 次。

目的仅是验证：

- 采集程序能看到 timing violation；
- candidate 判定能发现已知异常；
- evidence record 能正确关联原始数据。

它不是 cross-core hazard，不得作为论文的干扰发现结果。

### 负向控制

运行：

- `cpu_ctrl` 无 attacker；
- `cpu_ctrl` 配合低强度、非共享资源主导的 attacker；
- victim 无 attacker 的重复 baseline。

目的为估计系统噪声和假阳性率。

### 通过条件

- 正向控制 5 次中至少 4 次被识别；
- 正常 baseline 不应频繁被识别为 candidate；
- 如果正向控制失败，不进入搜索实验。

---

## E3：平衡式候选发现

### 固定搜索空间

搜索前生成并锁定 `search_space.yaml`，至少包括：

| 维度 | 建议取值 |
|---|---|
| victim | cache_sens、stream_mem、ptr_chase |
| attacker family | cache、memory |
| cache pattern | sequential、random |
| cache working set | 256 KiB、512 KiB、1 MiB、4 MiB、16 MiB |
| memory operation | read、write、copy |
| memory buffer | 16 MiB、64 MiB、128 MiB |
| duty cycle | 25%、50%、100% |
| attacker CPU | 所有非 victim 核 |
| attacker count | 1、2、3 |

不要求遍历全部组合。

### 发现预算

- 初始平衡探索：16 次，cache 与 memory 各 8 次；
- 自适应探索：最多 24 次；
- 总发现预算：最多 40 次正式 attack run；
- 每个 attack run 都必须有相邻或同 block 的 paired baseline。

AI 辅助体在自适应阶段优先选择：

1. 尚未覆盖的资源族或参数区域；
2. 接近判定边界、能减少不确定性的配置；
3. 可能区分 cache、memory 和环境效应的对照配置；
4. 已有候选附近但尚未验证剂量关系的配置。

AI 不得连续重复同一已知配置来制造高 hit rate。

### 输出

每次选择记录：

```text
run_id
selected_configuration
current_evidence
selection_reason
expected_information_gain
result
next_action
```

---

## E4：候选确认与证据收集

对每个初筛 candidate 执行以下协议。最多选择排名最高且机制不同的 6 个候选，避免确认预算失控。

### P1：独立重复

- 5 次 attack；
- 5 次 matched baseline；
- 两种 condition 的顺序随机化；
- 每次从相近起始温度开始。

如果 5 次 attack 中少于 4 次达到候选标准，标记为 `insufficient` 并停止该候选。

### P2：Attacker-off 与恢复

对通过 P1 的候选运行：

- attacker 停止后的立即 baseline；
- 冷却到起始温度后的 baseline；
- 至少各 3 次。

如果只有立即 baseline 异常、冷却后恢复，标记存在热历史或慢变环境混淆，不直接归因共享资源。

### P3：剂量和位置干预

至少执行：

- duty cycle 25%、50%、100%；
- attacker count 1、2、3；
- 两个不同 attacker CPU placement；
- 每个条件至少 3 次。

检查效果是否具有稳定的剂量—响应关系，以及是否符合共享拓扑预期。

### P4：环境对照

运行一个以计算和发热为主、但尽量少产生内存流量的 placebo attacker，并匹配相近温度。

目的为区分：

- 共享内存/cache 竞争；
- 温度、频率或系统运行时长造成的效应。

### P5：资源证据

对比 baseline、attack 和 intervention 的：

- victim P99 和 miss ratio；
- attacker throughput；
- cache/bus/PMU 信号；
- 温度与频率；
- victim 类型敏感度。

只在多项证据方向一致时给出候选机制。

---

## 6. 证据状态定义

每个候选只能进入以下一种状态：

### `supported`

- 独立重复稳定；
- paired baseline 正常；
- attacker-off 且环境恢复后效应消失；
- 至少一种剂量或位置干预符合预测；
- 环境对照不能单独复现同样效果。

### `environment_confounded`

- 效果与温度、频率、运行顺序或其他慢变状态不可分辨；
- 或 attacker 停止后仍持续，并且环境尚未恢复。

### `ambiguous_mechanism`

- timing hazard 可重复，但 cache 和 memory 等机制无法区分。

### `insufficient`

- 无法稳定复现；
- 效应低于阈值；
- 数据缺失；
- 干预结果互相矛盾。

不得使用 `confirmed_cache`、`confirmed_memory` 等更强标签，除非资源干预和观测证据确实能够区分机制。

---

## 7. E5：复合干扰实验

只有在 cache family 和 memory family 各得到至少一个可重复候选后才执行。

对 A=cache、B=memory 运行完整 2×2：

| 条件 | 最少重复数 |
|---|---:|
| baseline | 5 |
| A only | 5 |
| B only | 5 |
| A+B | 5 |

必须同时记录两个 attacker 的吞吐，避免把 attacker 相互降速误判为 victim 资源交互。

如果任一单通道候选不能复现，跳过复合实验并说明原因。不得在四格数据不完整时解释组合机制。

---

## 8. E6：预算—证据反馈演示

本阶段只演示闭环机制，不要求证明统计上的全面优势。

### 对照配置

使用相同搜索空间和总预算，运行三种策略：

1. `random`：随机选择；
2. `static_knowledge`：使用初始专家规则，但不接收证据反馈；
3. `evidence_feedback`：根据 `supported/confounded/insufficient` 更新优先级。

每种策略至少运行 3 个独立 campaign，使用不同随机种子。每个 campaign 的预算相同，并把 baseline、确认和干预实验都计入总成本。

### 必须汇总

- 每个预算位置发现的 candidate 数；
- verified hazard class 数；
- confounded/insufficient 数；
- 用于重复无效配置的预算；
- 首个 supported hazard 的总实验成本；
- evidence_feedback 因哪条证据改变了下一次选择。

如果没有任何 `supported` hazard，明确写为“搜索效率比较不具结论性”，只展示系统如何停止重复探索混淆区域。

---

## 9. E7：结构化 hazard record

AI 辅助体为每个候选生成一份 YAML，至少包含：

```yaml
hazard_id: H_IMX8MM_001
platform: imx8mm
victim:
  type: stream_mem
  parameters: {}
aggressor:
  family: memory
  parameters: {}
topology:
  victim_cpu: 1
  aggressor_cpus: [2]
  shared_resources: [l2, memory_controller]
effect:
  metric: p99_response_time
  paired_baseline: null
  attack_value: null
  slowdown: null
evidence:
  reproductions: []
  attacker_off: []
  interventions: []
  pmu: []
  environment: []
mechanism:
  candidates: []
  excluded: []
  unresolved: []
status: supported | environment_confounded | ambiguous_mechanism | insufficient
confidence: low | medium | high
limitations: []
evidence_paths: []
```

这一步只证明结构化记录可以生成和更新，不得声称已经证明跨平台迁移。

---

## 10. 停止条件

出现以下情况时 AI 辅助体应暂停，而不是继续消耗预算：

- 正向控制失败；
- baseline 自身频繁超过候选阈值；
- 温度无法恢复或频率持续异常；
- 连续 3 次出现 run ID、配置或 CSV 错配；
- attacker 没有产生预期吞吐；
- 同一候选经过 P1 后明显不可重复；
- 达到预注册总预算；
- 所有剩余搜索区域均因程序能力不足而无法执行。

暂停后生成 `BLOCKER_REPORT.md`，说明失败阶段、已有证据和建议动作。

---

## 11. 最终交付数据包

AI 辅助体最终提交：

```text
imx8mm-demo/
├── system_snapshot/
├── locked_protocol.yaml
├── search_space.yaml
├── manifest.csv
├── runs/
│   └── <run_id>/
│       ├── config.yaml
│       ├── victim.csv
│       ├── attacker.csv
│       ├── environment.csv
│       ├── perf.csv
│       ├── stdout.log
│       └── stderr.log
├── hazards/
│   └── H_IMX8MM_*.yaml
├── search_decisions.jsonl
├── summary_tables/
├── figures/
├── BLOCKER_REPORT.md        # 仅在暂停时产生
└── FINAL_DEMO_REPORT.md
```

`manifest.csv` 每行对应一次真实运行。禁止只提交汇总表而不提交原始证据。

---

## 12. FINAL_DEMO_REPORT.md 固定模板

最终报告必须按以下顺序输出：

1. 平台和锁定协议；
2. 原始运行总数及对账结果；
3. baseline 稳定性；
4. 正向/负向控制结果；
5. 搜索空间和实际覆盖范围；
6. 所有 candidate 的证据状态；
7. 每个 supported/confounded candidate 的完整证据；
8. 预算—证据反馈轨迹；
9. PMU、温度、频率和 attacker throughput 汇总；
10. 未完成或失败的实验；
11. Demo 等级：A、B 或 C；
12. 允许得出的结论；
13. 明确不能得出的结论。

报告最后回答以下问题：

```text
Q1. 数据和实验身份是否完全可追踪？
Q2. 每种 victim 是否使用自己的 paired baseline？
Q3. 检测器是否通过已知正向控制？
Q4. 是否存在可重复的 cross-core timing hazard？
Q5. 是否有表面阳性被证据协议降级？
Q6. 是否能区分资源竞争和环境混淆？
Q7. 证据是否实际改变过后续搜索选择？
Q8. 是否生成了可审计的结构化 hazard record？
Q9. 当前结果属于 A、B 还是 C？
Q10. 哪些主张必须留到多平台实验？
```

这份最终数据包将用于判断 i.MX8MM 单板 demo 是否成功，以及哪些结果可以进入论文、哪些只能作为工程调试记录。
