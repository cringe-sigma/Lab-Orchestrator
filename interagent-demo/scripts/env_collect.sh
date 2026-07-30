#!/bin/bash
# 行动项 A: 采集 i.MX8MM 环境信息
set -e
DEMO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$DEMO_DIR/results/environment"
mkdir -p "$OUT"

echo "=== InterAgent Demo: Environment Collection ==="

# A1: 基础信息
uname -a                  >  "$OUT/uname.txt"
cat /etc/os-release       >  "$OUT/os-release.txt" 2>/dev/null || true
cat /proc/cmdline         >  "$OUT/cmdline.txt"
lscpu                     >  "$OUT/lscpu.txt"
cat /proc/cpuinfo         >  "$OUT/cpuinfo.txt"

# A2: cache / freq / thermal
find /sys/devices/system/cpu/cpu0/cache -maxdepth 2 -type f -print > "$OUT/cache_sysfs.txt" 2>/dev/null || true

for cpu in 0 1 2 3; do
    f="/sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_cur_freq"
    [ -f "$f" ] && echo "cpu$cpu: $(cat $f)" >> "$OUT/cpu_freq.txt"
    g="/sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_governor"
    [ -f "$g" ] && echo "cpu$cpu governor: $(cat $g)" >> "$OUT/cpu_governor.txt"
done

find /sys/class/thermal -name temp -print > "$OUT/thermal_zones.txt" 2>/dev/null || true
for t in $(cat "$OUT/thermal_zones.txt" 2>/dev/null); do
    echo "$t: $(cat $t 2>/dev/null)" >> "$OUT/thermal_values.txt"
done

# A3: kernel type
if [ -f /sys/kernel/realtime ]; then
    cat /sys/kernel/realtime > "$OUT/kernel_realtime.txt"
fi
zcat /proc/config.gz 2>/dev/null | grep -E 'PREEMPT|PERF_EVENTS|BPF|FTRACE|TRACING' > "$OUT/kernel_config_preempt.txt" || true
if [ -f /boot/config-$(uname -r) ]; then
    grep -E 'PREEMPT|PERF_EVENTS|BPF|FTRACE|TRACING' /boot/config-$(uname -r) > "$OUT/kernel_config_preempt.txt"
fi

# perf
if command -v perf &>/dev/null; then
    perf --version > "$OUT/perf_version.txt" 2>/dev/null || true
    perf list 2>/dev/null | head -80 > "$OUT/perf_list.txt" || true
    perf stat -e cycles,instructions,cache-references,cache-misses sleep 1 > "$OUT/perf_stat.txt" 2>&1 || true
else
    echo "PMU unavailable: perf not found" > "$OUT/perf_status.txt"
fi

echo "=== Done: $OUT ==="
ls -la "$OUT/"
