# InterAgent i.MX8MM 最小可执行 Demo 行动计划

## 1. Demo 最终目标

仅使用现有 i.MX8MM 环境，完成以下闭环：

```text
识别 Linux 环境
→ 建立可重复的 victim 基线
→ 人工制造跨核 cache/memory 干扰
→ 自动搜索干扰参数
→ 自动执行重复实验和负对照
→ 输出一条结构化 timing-hazard record
→ 与 random search 做同预算比较
```

本 Demo 暂时不要求：

- PREEMPT_RT；
- Raspberry Pi 4/5；
- 跨平台迁移；
- 精确复现 PolyRhythm；
- IRQ、TLB、内核锁等其他资源；
- 强化学习、LLM agent 或复杂多-agent通信；
- 安全 WCET 上界或唯一硬件根因。

最终验收标准：

> 在 i.MX8MM 上，系统能在固定实验预算内自动发现至少一个可重复的跨核 timing hazard，执行至少两个负对照，并输出结论不超过 `cache/memory path` 粒度的结构化证据记录。

---

## 2. 建议目录结构

在 i.MX8MM 上建立：

```text
interagent-demo/
├── bin/                 # 编译后的 victim 和 attacker
├── src/                 # C/C++ 源代码
├── contracts/           # YAML 干扰契约
├── scripts/             # 环境采集、单次实验、搜索、验证脚本
├── configs/             # 实验参数
├── results/
│   ├── environment/     # 系统和硬件信息
│   ├── baseline/        # victim 隔离运行结果
│   ├── discovery/       # 搜索阶段结果
│   ├── confirmation/    # 独立确认结果
│   └── hazards/         # 最终 hazard records
└── README.md
```

所有实验结果至少包含：实验编号、时间、Git commit、内核版本、CPU affinity、victim 参数、attacker 参数、持续时间、随机种子、温度、CPU 频率和退出状态。

---

## 3. 行动项 A：识别并保存当前 Linux 环境

### A1. 采集基础信息

在板子上依次执行：

```bash
mkdir -p interagent-demo/results/environment
cd interagent-demo

uname -a | tee results/environment/uname.txt
cat /etc/os-release | tee results/environment/os-release.txt
cat /proc/cmdline | tee results/environment/cmdline.txt
lscpu | tee results/environment/lscpu.txt
cat /proc/cpuinfo | tee results/environment/cpuinfo.txt
```

如果存在以下文件，再执行：

```bash
cat /sys/kernel/realtime
zcat /proc/config.gz | grep -E 'PREEMPT|PERF_EVENTS|BPF|FTRACE|TRACING'
cat /boot/config-$(uname -r) | grep -E 'PREEMPT|PERF_EVENTS|BPF|FTRACE|TRACING'
```

允许部分命令因文件不存在而失败。只需记录真实情况，不必立刻更换内核。

### A2. 采集 CPU、cache、频率和温度信息

```bash
find /sys/devices/system/cpu/cpu0/cache -maxdepth 2 -type f -print
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
find /sys/class/thermal -name temp -print
```

如存在 `perf`，执行：

```bash
perf --version
perf list | head -n 80
perf stat -e cycles,instructions,cache-references,cache-misses sleep 1
```

如 `perf` 不存在或 PMU 无权限，先记录为 `PMU unavailable`。Demo 可以仅依靠 response time 完成，PMU 是附加证据而非阻塞项。

### A3. 判断当前内核类型

按以下规则记录：

- `/sys/kernel/realtime` 输出 `1`：记录为 PREEMPT_RT；
- kernel config 包含 `CONFIG_PREEMPT_RT=y`：记录为 PREEMPT_RT；
- 包含 `CONFIG_PREEMPT=y` 但没有 `CONFIG_PREEMPT_RT=y`：记录为 preemptible Linux；
- 包含 `CONFIG_PREEMPT_NONE=y`：记录为 non-preemptible Linux；
- 无法获取 config：记录为 unknown，不阻塞 Demo。

### A4. 完成条件

- [ ] `results/environment/` 中保存系统信息；
- [ ] 明确内核版本；
- [ ] 明确是否能够读取 CPU frequency 和温度；
- [ ] 明确 `perf` 是否可用；
- [ ] 明确 PREEMPT_RT 状态，允许结果为 unknown；
- [ ] 不因缺少 PREEMPT_RT 而更换系统。

---

## 4. 行动项 B：实现一个最小 victim

### B1. Victim 行为

实现一个 C/C++ 周期任务：

1. 使用单调时钟记录时间；
2. 每个周期遍历固定大小的内存数组；
3. 使用绝对时间睡眠进入下一个周期；
4. 每周期输出：release time、start time、finish time、execution time、response time；
5. 支持命令行指定工作集、周期、运行时长和 CPU；
6. 通过 `taskset` 固定在一个 CPU 上。

建议初始参数：

```text
victim CPU：1
working set：1 MiB
period：10 ms
duration：60 s
```

如果任务执行时间过短难以测量，逐步增加工作集或数组遍历次数，但保持隔离运行时不发生 deadline miss。

### B2. 建立隔离基线

在没有 attacker 时独立运行至少 10 次，每次 60 秒，记录：

- median response time；
- P95；
- P99；
- maximum；
- 每次运行的 CPU 频率和开始/结束温度。

Demo 的临时 deadline 可以定义为：

```text
deadline = 隔离运行总体 P99 × 1.5
```

该 deadline 仅用于 Demo 的风险判定，不代表安全 WCET 或正式实时保证。

### B3. 完成条件

- [ ] victim 可以运行 60 秒且输出逐周期 CSV；
- [ ] victim 固定在指定 CPU；
- [ ] 完成至少 10 次隔离运行；
- [ ] 生成 `results/baseline/summary.csv`；
- [ ] 确定 Demo deadline；
- [ ] 基线异常时先排查频率、温度和后台负载，不进入搜索阶段。

---

## 5. 行动项 C：实现两个最小 attacker

### C1. Cache attacker

功能：反复访问指定大小的内存区域。

支持参数：

```text
working set：256 KiB / 1 MiB / 4 MiB / 16 MiB
access：sequential / random
CPU：0 / 2 / 3
duration：60 s
```

### C2. Memory attacker

功能：持续读取、写入或复制较大内存区域。

支持参数：

```text
working set：16 MiB / 64 MiB / 128 MiB
operation：read / write / copy
attacker count：1 / 2
CPU：0 / 2 / 3
duration：60 s
```

参数过多时，第一轮只保留：

```text
cache working set：1 / 4 / 16 MiB
memory working set：16 / 64 / 128 MiB
operation：read / write
attacker count：1
```

### C3. 手工确认干扰存在

在编写自动搜索前，手工验证：

1. victim 单独运行；
2. victim 与 cache attacker 共置；
3. victim 与 memory attacker 共置；
4. attacker 关闭后再次运行 victim。

至少找到一个使 victim P99 response time 上升 20% 以上，或产生 Demo deadline miss 的配置。

如果没有达到 20%，不要立刻改变研究问题，按顺序尝试：

1. 增大 attacker working set；
2. 增大 victim 工作量；
3. 改变 attacker CPU；
4. 使用两个 attacker；
5. 延长实验时间。

### C4. 完成条件

- [ ] 两个 attacker 均可指定 CPU 和参数；
- [ ] 找到至少一个候选干扰配置；
- [ ] attacker 关闭后现象明显减弱或消失；
- [ ] 保存人工验证命令和全部原始数据。

---

## 6. 行动项 D：建立两个最小可执行契约

先使用 YAML 文件，不建设数据库。

### D1. Cache-path 契约

```yaml
id: cache_path_v1
resource_family: cache_memory_path

generator:
  name: cache_attacker
  parameters:
    working_set_kib: [1024, 4096, 16384]
    access: [sequential, random]
    cpu: [0, 2, 3]

victim:
  cpu: 1

observations:
  required:
    - victim_response_time
  optional:
    - cache_misses

negative_controls:
  - attacker_disabled
  - small_working_set
  - attacker_cpu_changed

conclusion_limit: cache_memory_path
```

### D2. Memory-path 契约

```yaml
id: memory_path_v1
resource_family: cache_memory_path

generator:
  name: memory_attacker
  parameters:
    working_set_mib: [16, 64, 128]
    operation: [read, write]
    cpu: [0, 2, 3]

victim:
  cpu: 1

observations:
  required:
    - victim_response_time
  optional:
    - cache_misses
    - memory_events

negative_controls:
  - attacker_disabled
  - small_working_set
  - attacker_cpu_changed

conclusion_limit: cache_memory_path
```

两个契约目前可以共享同一个 `resource_family`。在没有特异性干预和足够 PMU 证据时，不区分 cache capacity 与 DRAM bandwidth 根因。

### D3. 完成条件

- [ ] 两个 YAML 文件可以被程序解析；
- [ ] 搜索参数来自 YAML，而非写死在搜索代码中；
- [ ] 负对照定义来自 YAML；
- [ ] 程序不能输出超过 `conclusion_limit` 的结论。

---

## 7. 行动项 E：实现最小搜索程序

### E1. 第一版不做复杂多-agent

实现三个普通软件模块即可：

```text
CacheAgent
  从 cache_path_v1.yaml 生成候选

MemoryAgent
  从 memory_path_v1.yaml 生成候选

Coordinator
  决定下一次运行哪个候选并记录预算
```

“Agent”只表示负责一个契约空间的候选生成器，不需要消息中间件、LLM 或强化学习。

### E2. 最小预算策略

总预算先设为 30 次 discovery experiments：

1. CacheAgent 随机执行 5 次；
2. MemoryAgent 随机执行 5 次；
3. 剩余 20 次中，80% 分给当前有效候选率更高的 agent；
4. 保留 20% 继续随机探索另一个 agent；
5. discovery 阶段只生成候选，不直接报告最终 hazard。

候选阈值：

```text
P99 response time 相对基线上升至少 20%
或者
出现 Demo deadline miss
```

### E3. 保存搜索轨迹

每次实验保存：

```text
experiment_id
agent
configuration
start_time
duration
p50/p95/p99/max
deadline_miss_count
temperature_before/after
frequency_before/after
candidate_yes_no
```

### E4. 完成条件

- [ ] 一条命令可以启动 30 次实验；
- [ ] 中断后能够从最后一个实验继续；
- [ ] 生成完整搜索轨迹 CSV/JSON；
- [ ] 返回候选列表；
- [ ] 搜索阶段候选不会直接被标记为最终 hazard。

---

## 8. 行动项 F：自动确认和负对照

对 discovery 阶段最好的 3 个候选分别执行：

1. 原配置独立重复 5 次；
2. attacker disabled 重复 3 次；
3. small working set 重复 3 次；
4. attacker CPU changed 重复 3 次；
5. 恢复原配置再重复 3 次。

Demo 判定规则：

- 原配置的 5 次确认中至少 4 次超过候选阈值；
- attacker disabled 后效应明显降低；
- 至少一个额外负对照使效应明显降低；
- 最后恢复原配置后能够再次复现；
- 若温度或频率变化可以独立解释现象，则输出 `environment-confounded`，不报告 validated hazard。

允许的最终状态：

```text
supported
contradicted
insufficient-evidence
environment-confounded
```

### 完成条件

- [ ] confirmation 使用与 discovery 分离的运行数据；
- [ ] 自动执行至少两个负对照；
- [ ] 自动给出四种状态之一；
- [ ] 失败和 confounded 结果同样保存，不得删除。

---

## 9. 行动项 G：生成最终 hazard record

输出 YAML：

```yaml
hazard_id: imx8mm-cache-memory-001
platform: imx8mm
kernel: unknown-until-collected

victim:
  name: periodic_memory_victim
  cpu: 1
  period_ms: 10
  deadline_definition: baseline_p99_x_1.5

effect:
  p99_increase_percent: 0
  deadline_miss_before: 0
  deadline_miss_after: 0

configuration:
  generator: memory_attacker
  attacker_cpu: 2
  working_set_mib: 64
  operation: write

hypothesis:
  resource_family: cache_memory_path
  status: supported
  fine_grained_attribution: unresolved

evidence:
  independent_reproduction: passed
  attacker_disabled: passed
  small_working_set: passed
  attacker_cpu_changed: passed
  pmu: unavailable_or_recorded
  environment_check: passed

artifacts:
  discovery_result: path/to/result
  confirmation_result: path/to/result
  reproduction_command: path/to/script
```

### 完成条件

- [ ] 自动生成至少一份 hazard YAML；
- [ ] YAML 引用原始数据路径和复现命令；
- [ ] 未区分清楚 cache/memory 时明确写 `unresolved`；
- [ ] 从新终端运行复现命令可以再次观察现象。

---

## 10. 行动项 H：加入一个最小对照实验

只比较：

1. Random search；
2. InterAgent 的两阶段 agent 预算分配。

要求：

- 使用相同候选空间；
- 使用相同的 30 次 discovery 预算；
- 使用不同随机种子重复若干轮；
- confirmation 和负对照成本均计入总成本。

比较指标：

- 第一次发现可确认 hazard 所需实验次数；
- 30 次预算内得到的 validated hazards 数量；
- discovery candidates 中最终通过确认的比例；
- 总 wall-clock 时间。

此阶段不称为 PolyRhythm 复现，也不声称证明完整论文贡献。它只用于确认 Demo 的预算分配逻辑值得继续开发。

### 完成条件

- [ ] 两种方法使用完全相同的配置集合；
- [ ] 生成一张简单对比表或曲线；
- [ ] 无论 InterAgent 是否胜出，都保留结果；
- [ ] 若没有优势，先修改搜索策略，不扩展到其他平台。

---

## 11. 推荐执行顺序与时间盒

### 第 1–2 天：环境与基线

- [ ] 完成行动项 A；
- [ ] 完成 victim；
- [ ] 取得 10 次隔离基线。

### 第 3–4 天：制造干扰

- [ ] 完成两个 attacker；
- [ ] 手工找到至少一个有效配置；
- [ ] 保存全部命令和数据。

### 第 5–6 天：契约与自动搜索

- [ ] 完成两个 YAML 契约；
- [ ] 实现 CacheAgent、MemoryAgent、Coordinator；
- [ ] 跑通 30 次自动实验。

### 第 7–8 天：确认与报告

- [ ] 自动执行重复和负对照；
- [ ] 生成第一条 hazard record；
- [ ] 验证一键复现。

### 第 9–10 天：最小对照

- [ ] 实现 random baseline；
- [ ] 使用相同预算比较；
- [ ] 总结 Demo 是否值得扩展。

时间安排是建议时间盒，不要求机械遵守。若前一步验收未通过，不进入后一步。

---

## 12. Demo 结束后的唯一决策点

Demo 完成后，根据结果只做一个决策：

### 若闭环成功

下一步优先增加 Pi 4 或 Pi 5，验证契约和 hazard record 能否作为目标平台搜索先验。此时再考虑 PREEMPT_RT 和 PolyRhythm-style baseline。

### 若能制造干扰但自动搜索无优势

保留平台、victim、attacker 和证据链，优先改进预算策略，不扩展平台。

### 若无法稳定制造干扰

先检查 CPU/cache 拓扑、频率、温度、victim 强度和 attacker 工作集；仍失败时更换 victim 或 stressor，不开始多-agent与迁移开发。

### 若证据无法区分 cache 与 memory

这是允许的结果。统一输出 `cache/memory path supported; fine-grained attribution unresolved`，不要阻塞 Demo，也不要制造更精细的标签。

---

## 13. 最终交付物清单

- [ ] i.MX8MM 环境报告；
- [ ] victim 源码与基线结果；
- [ ] cache attacker 和 memory attacker；
- [ ] 两个 YAML 契约；
- [ ] 30 次预算搜索程序；
- [ ] 自动 confirmation 和负对照程序；
- [ ] 至少一条 hazard record；
- [ ] 一键复现命令；
- [ ] random 与 InterAgent 的最小对照结果；
- [ ] 一页 Demo 总结：成功、失败、未决问题和下一步。

只有以上项目全部完成后，才进入多平台、跨平台迁移和正式论文实验阶段。
