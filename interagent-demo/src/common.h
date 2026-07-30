/* InterAgent i.MX8MM Demo — 共享头文件 */
#ifndef COMMON_H
#define COMMON_H

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>
#include <sched.h>
#include <pthread.h>
#include <errno.h>

/* ========== 时间工具 ========== */
static inline uint64_t monotonic_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

/* ========== CPU affinity ========== */
static inline int pin_to_cpu(int cpu) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(cpu, &cpuset);
    return sched_setaffinity(0, sizeof(cpuset), &cpuset);
}

/* ========== 温度读取 (i.MX8MM) ========== */
static inline int read_temp_mC(void) {
    FILE *f = fopen("/sys/class/thermal/thermal_zone0/temp", "r");
    if (!f) return -1;
    int t;
    fscanf(f, "%d", &t);
    fclose(f);
    return t;
}

/* ========== 频率读取 ========== */
static inline int read_cpu_freq_khz(int cpu) {
    char path[128];
    snprintf(path, sizeof(path),
             "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq", cpu);
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    int freq;
    fscanf(f, "%d", &freq);
    fclose(f);
    return freq;
}

/* ========== 内存访问工具 ========== */
static inline void touch_memory_sequential(char *buf, size_t size, size_t stride) {
    volatile char *p = (volatile char *)buf;
    for (size_t i = 0; i < size; i += stride) {
        p[i] = (char)i;
    }
}

static inline void touch_memory_random(char *buf, size_t size, size_t stride, unsigned int *seed) {
    volatile char *p = (volatile char *)buf;
    size_t steps = size / stride;
    for (size_t i = 0; i < steps; i++) {
        size_t idx = (rand_r(seed) % steps) * stride;
        p[idx] = (char)i;
    }
}

#endif /* COMMON_H */
