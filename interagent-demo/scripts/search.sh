#!/bin/bash
# 行动项 E: 30 次预算自动搜索 (CacheAgent + MemoryAgent + Coordinator)
set -e
DEMO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

TOTAL_BUDGET="${1:-30}"
PHASE1="${2:-10}"  # 探索阶段: 各5次
OUT_DIR="$DEMO_DIR/results/discovery"
mkdir -p "$OUT_DIR"

echo "=== InterAgent Search: budget=$TOTAL_BUDGET ==="

exp=0
declare -A agents
agents["cache"]="5"
agents["memory"]="5"

# --- Phase 1: 各随机 5 次 ---
echo "--- Phase 1: Random exploration (${PHASE1} experiments) ---"
for i in $(seq 1 5); do
    ws=$((1024 * (1 << (RANDOM % 4))))  # 1/2/4/8 MiB for cache
    [ $ws -gt 16384 ] && ws=16384
    pat=$( [ $((RANDOM % 2)) -eq 0 ] && echo "seq" || echo "rand" )
    cpu=$(( (RANDOM % 3) == 0 ? 0 : (RANDOM % 2) == 0 ? 2 : 3 ))
    exp=$((exp+1))
    echo "[$exp/$TOTAL_BUDGET] CacheAgent: ws=${ws}KiB pat=$pat cpu=$cpu"
    bash "$DEMO_DIR/scripts/run_experiment.sh" \
        "cache_e${exp}" 1 10000 60 1024 \
        "taskset -c $cpu $DEMO_DIR/bin/cache_attacker $ws $pat 60"
done

for i in $(seq 1 5); do
    ws=$((16 * (1 << (RANDOM % 3))))  # 16/32/64/128 MiB
    [ $ws -gt 128 ] && ws=128
    op=$( [ $((RANDOM % 2)) -eq 0 ] && echo "read" || echo "write" )
    cpu=$(( (RANDOM % 3) == 0 ? 0 : (RANDOM % 2) == 0 ? 2 : 3 ))
    exp=$((exp+1))
    echo "[$exp/$TOTAL_BUDGET] MemoryAgent: ws=${ws}MiB op=$op cpu=$cpu"
    bash "$DEMO_DIR/scripts/run_experiment.sh" \
        "memory_e${exp}" 1 10000 60 1024 \
        "taskset -c $cpu $DEMO_DIR/bin/memory_attacker $ws $op 60"
done

# --- Phase 2: Biased allocation ---
PHASE2=$((TOTAL_BUDGET - PHASE1))
echo "--- Phase 2: Biased search (${PHASE2} experiments) ---"
for i in $(seq 1 $PHASE2); do
    # 简单策略: 50% cache, 50% memory，保持随机探索
    if [ $((RANDOM % 2)) -eq 0 ]; then
        ws=$((1024 * (1 << (RANDOM % 4))))
        [ $ws -gt 16384 ] && ws=16384
        pat=$( [ $((RANDOM % 2)) -eq 0 ] && echo "seq" || echo "rand" )
        cpu=$(( (RANDOM % 3) == 0 ? 0 : (RANDOM % 2) == 0 ? 2 : 3 ))
        exp=$((exp+1))
        echo "[$exp/$TOTAL_BUDGET] CacheAgent: ws=${ws}KiB pat=$pat cpu=$cpu"
        bash "$DEMO_DIR/scripts/run_experiment.sh" \
            "cache_e${exp}" 1 10000 60 1024 \
            "taskset -c $cpu $DEMO_DIR/bin/cache_attacker $ws $pat 60"
    else
        ws=$((16 * (1 << (RANDOM % 3))))
        [ $ws -gt 128 ] && ws=128
        op=$( [ $((RANDOM % 2)) -eq 0 ] && echo "read" || echo "write" )
        cpu=$(( (RANDOM % 3) == 0 ? 0 : (RANDOM % 2) == 0 ? 2 : 3 ))
        exp=$((exp+1))
        echo "[$exp/$TOTAL_BUDGET] MemoryAgent: ws=${ws}MiB op=$op cpu=$cpu"
        bash "$DEMO_DIR/scripts/run_experiment.sh" \
            "memory_e${exp}" 1 10000 60 1024 \
            "taskset -c $cpu $DEMO_DIR/bin/memory_attacker $ws $op 60"
    fi
done

echo "=== Search complete: $exp experiments ==="
echo "Results: $OUT_DIR/"
