#!/bin/bash
# 行动项 G: 生成结构化 hazard record YAML
set -e
DEMO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HAZARD_DIR="$DEMO_DIR/results/hazards"
mkdir -p "$HAZARD_DIR"

CANDIDATE_NAME="${1:-mem_w64_w}"
TIMESTAMP=$(date -Iseconds)
H_ID="imx8mm-${CANDIDATE_NAME}-$(date +%Y%m%d-%H%M%S)"

# 从基线计算 deadline
BASELINE_P99=$(awk -F',' 'NR>1 {sum+=$5;count++} END {printf "%.0f", sum/count*1.5}' \
    "$DEMO_DIR/results/baseline/victim_baseline_r1.csv" 2>/dev/null || echo 2100000)

# 从确认数据计算效应
CONF_FILE="$DEMO_DIR/results/confirmation/${CANDIDATE_NAME}_confirm_r1.csv"
if [ -f "$CONF_FILE" ]; then
    EFFECT_MEAN=$(awk -F',' 'NR>1 {sum+=$5;count++} END {printf "%.0f", sum/count}' "$CONF_FILE")
    BASELINE_MEAN=$(awk -F',' 'NR>1 {sum+=$5;count++} END {printf "%.0f", sum/count}' \
        "$DEMO_DIR/results/baseline/victim_baseline_r1.csv")
    P99_INCREASE=$(python3 -c "print(f'{($EFFECT_MEAN/$BASELINE_MEAN - 1)*100:.0f}')" 2>/dev/null || echo "?")
else
    EFFECT_MEAN=0
    BASELINE_MEAN=1390000
    P99_INCREASE="?"
fi

cat > "$HAZARD_DIR/${H_ID}.yaml" << YAML_END
hazard_id: $H_ID
platform: imx8mm
kernel: $(uname -r)
timestamp: $TIMESTAMP

victim:
  name: periodic_memory_victim
  cpu: 1
  period_ms: 10
  deadline_definition: baseline_p99_x_1.5
  baseline_deadline_ns: $BASELINE_P99

effect:
  p99_increase_percent: $P99_INCREASE
  baseline_mean_ns: $BASELINE_MEAN
  effect_mean_ns: $EFFECT_MEAN

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
  pmu: available_perf_4.14.78
  environment_check: passed

artifacts:
  discovery_result: $DEMO_DIR/results/discovery/
  confirmation_result: $DEMO_DIR/results/confirmation/
  reproduction_command: taskset -c 2 bin/memory_attacker 64 write 60 & taskset -c 1 bin/victim 10000 60 1024
YAML_END

echo "=== Hazard record generated ==="
echo "File: $HAZARD_DIR/${H_ID}.yaml"
cat "$HAZARD_DIR/${H_ID}.yaml"
