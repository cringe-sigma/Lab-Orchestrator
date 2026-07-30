#!/bin/bash
# 行动项 F: 对 top 3 候选执行确认 + 负对照
set -e
DEMO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONF_DIR="$DEMO_DIR/results/confirmation"
mkdir -p "$CONF_DIR"

echo "=== Confirmation & Negative Controls ==="

# 硬编码之前手工验证找到的候选配置
# (正式使用时应从 discovery 结果自动选取 top 3)
CANDIDATES=(
  "mem_w64_w 64 write 2 memory_attacker"
  "cache_s4_seq 4 seq 2 cache_attacker"  # 4MiB = 4096 KiB
)

for candidate in "${CANDIDATES[@]}"; do
  read -r name ws op cpu tool <<< "$candidate"
  echo ""
  echo "====== Candidate: $name ($tool ws=$ws op=$op cpu=$cpu) ======"

  # 1. 原配置重复 5 次
  for r in $(seq 1 5); do
    echo "[confirm-$name] reproduction $r/5"
    taskset -c "$cpu" "$DEMO_DIR/bin/$tool" "$ws" "$op" 60 &
    AT_PID=$!
    sleep 1
    taskset -c 1 "$DEMO_DIR/bin/victim" 10000 60 1024 \
      "$CONF_DIR/${name}_confirm_r${r}.csv" 2>"$CONF_DIR/${name}_confirm_r${r}_log.txt"
    kill $AT_PID 2>/dev/null; wait 2>/dev/null
  done

  # 2. attacker disabled 3 次 (负对照 1)
  for r in $(seq 1 3); do
    echo "[confirm-$name] attacker_disabled $r/3"
    taskset -c 1 "$DEMO_DIR/bin/victim" 10000 60 1024 \
      "$CONF_DIR/${name}_nodisrupt_r${r}.csv" 2>"$CONF_DIR/${name}_nodisrupt_r${r}_log.txt"
  done

  # 3. small working set 3 次 (负对照 2)
  small_ws=$(( ws / 4 ))
  [ "$tool" = "cache_attacker" ] && small_ws=1024   # 1MiB for cache
  [ "$tool" = "memory_attacker" ] && small_ws=16     # 16MiB for memory
  for r in $(seq 1 3); do
    echo "[confirm-$name] small_ws($small_ws) $r/3"
    taskset -c "$cpu" "$DEMO_DIR/bin/$tool" "$small_ws" "$op" 60 &
    AT_PID=$!
    sleep 1
    taskset -c 1 "$DEMO_DIR/bin/victim" 10000 60 1024 \
      "$CONF_DIR/${name}_smallws_r${r}.csv" 2>"$CONF_DIR/${name}_smallws_r${r}_log.txt"
    kill $AT_PID 2>/dev/null; wait 2>/dev/null
  done

  # 4. attacker CPU changed 3 次 (负对照 3)
  alt_cpu=$(( (cpu + 1) % 4 ))
  [ $alt_cpu -eq 1 ] && alt_cpu=0
  for r in $(seq 1 3); do
    echo "[confirm-$name] cpu_changed(cpu=$alt_cpu) $r/3"
    taskset -c "$alt_cpu" "$DEMO_DIR/bin/$tool" "$ws" "$op" 60 &
    AT_PID=$!
    sleep 1
    taskset -c 1 "$DEMO_DIR/bin/victim" 10000 60 1024 \
      "$CONF_DIR/${name}_cpuchanged_r${r}.csv" 2>"$CONF_DIR/${name}_cpuchanged_r${r}_log.txt"
    kill $AT_PID 2>/dev/null; wait 2>/dev/null
  done
done

echo ""
echo "=== Confirmation complete ==="
ls -la "$CONF_DIR/"
