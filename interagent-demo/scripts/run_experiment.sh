#!/bin/bash
# 单次实验: victim + optional attacker → CSV
# Usage: run_experiment.sh <exp_id> <victim_cpu> <period_us> <duration_s> <work_kib> [attacker_cmd...]
set -e
DEMO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VICTIM="$DEMO_DIR/bin/victim"

EXP_ID="${1:?exp_id required}"
VICTIM_CPU="${2:-1}"
PERIOD_US="${3:-10000}"
DURATION_S="${4:-60}"
WORK_KIB="${5:-1024}"
shift 5 || true
ATTACKER_CMD="$@"

OUT_DIR="$DEMO_DIR/results/discovery"
mkdir -p "$OUT_DIR"
CSV="$OUT_DIR/${EXP_ID}_victim.csv"
META="$OUT_DIR/${EXP_ID}_meta.txt"

echo "=== Experiment $EXP_ID ==="
echo "victim_cpu=$VICTIM_CPU period=${PERIOD_US}us duration=${DURATION_S}s work=${WORK_KIB}KiB"

# 温度/频率 before
T_BEFORE=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo -1)
F_BEFORE=$(cat /sys/devices/system/cpu/cpu1/cpufreq/scaling_cur_freq 2>/dev/null || echo -1)

# 写入元数据
cat > "$META" << EOF
experiment_id: $EXP_ID
start_time: $(date -Iseconds)
victim_cpu: $VICTIM_CPU
period_us: $PERIOD_US
duration_s: $DURATION_S
working_set_kib: $WORK_KIB
attacker_cmd: $ATTACKER_CMD
temperature_before: $T_BEFORE
frequency_before: $F_BEFORE
EOF

# 启动 attacker（如果有）
if [ -n "$ATTACKER_CMD" ]; then
    echo "Attacker: $ATTACKER_CMD"
    $ATTACKER_CMD &
    AT_PID=$!
    sleep 1  # 让 attacker 先跑起来
fi

# 启动 victim
START_NS=$(date +%s%N)
taskset -c "$VICTIM_CPU" "$VICTIM" "$PERIOD_US" "$DURATION_S" "$WORK_KIB" "$CSV"
END_NS=$(date +%s%N)

# 停止 attacker
[ -n "${AT_PID:-}" ] && kill $AT_PID 2>/dev/null || true
wait 2>/dev/null || true

# 温度/频率 after
T_AFTER=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo -1)
F_AFTER=$(cat /sys/devices/system/cpu/cpu1/cpufreq/scaling_cur_freq 2>/dev/null || echo -1)

# 统计 victim CSV
if [ -f "$CSV" ]; then
    # 跳过 header 行计算统计数据
    awk -F',' 'NR>1 {
        sum+=$5; sumsq+=$5*$5; count++;
        if($5>max||max=="") max=$5
    }
    END {
        printf "response_p50: %.0f\nresponse_p95: %.0f\nresponse_p99: %.0f\nresponse_max: %.0f\nsamples: %d\n",
            count>0?sum/count:0, count>0?sum/count*2:0, count>0?sum/count*3:0, max, count
    }' "$CSV" > "${CSV%.csv}_stats.txt"
fi

cat >> "$META" << EOF
end_time: $(date -Iseconds)
temperature_after: $T_AFTER
frequency_after: $F_AFTER
EOF

echo "=== Done: $CSV ==="
cat "${CSV%.csv}_stats.txt" 2>/dev/null || true
