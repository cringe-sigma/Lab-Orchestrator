/*
 * InterAgent Demo — Periodic Memory Victim
 *
 * 行为: 固定周期遍历内存数组，输出每周期 timing 到 stdout (CSV)
 * CSV: release_ns, start_ns, finish_ns, exec_ns, resp_ns
 *
 * 用法:
 *   taskset -c <cpu> ./victim <period_us> <duration_s> <working_set_kib> [csv_file]
 */
#include "common.h"
#include <signal.h>

static volatile int running = 1;

static void sig_handler(int sig) { running = 0; }

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: victim <period_us> <duration_s> <working_set_kib> [csv_out]\n");
        return 1;
    }

    long   period_us  = atol(argv[1]);
    int    duration_s = atoi(argv[2]);
    size_t work_kib   = (size_t)atol(argv[3]);
    const char *out_file = (argc >= 5) ? argv[4] : NULL;

    size_t work_bytes = work_kib * 1024;
    char *buf = (char *)malloc(work_bytes);
    if (!buf) { perror("malloc"); return 1; }
    memset(buf, 0xAA, work_bytes);

    FILE *out = out_file ? fopen(out_file, "w") : stdout;
    if (!out) { perror("fopen"); free(buf); return 1; }

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    /* 记录环境 */
    int temp_before = read_temp_mC();
    int freq_before = read_cpu_freq_khz(sched_getcpu());

    fprintf(stderr, "# victim: period=%ldus duration=%ds work=%zuKiB\n",
            period_us, duration_s, work_kib);
    fprintf(stderr, "# temp_before=%d freq_before=%d\n", temp_before, freq_before);

    if (out != stdout)
        fprintf(out, "release_ns,start_ns,finish_ns,exec_ns,resp_ns\n");

    uint64_t t0     = monotonic_ns();
    uint64_t period_ns = period_us * 1000ULL;
    uint64_t next_release = t0;
    uint64_t deadline_ns   = t0 + (uint64_t)duration_s * 1000000000ULL;
    size_t   stride        = 64;  /* cache line stride */

    while (running && monotonic_ns() < deadline_ns) {
        uint64_t release = monotonic_ns();

        /* --- 周期工作: 遍历数组 --- */
        uint64_t start  = monotonic_ns();
        touch_memory_sequential(buf, work_bytes, stride);
        uint64_t finish = monotonic_ns();

        uint64_t exec_time  = finish - start;
        uint64_t resp_time  = finish - release;

        fprintf(out, "%llu,%llu,%llu,%llu,%llu\n",
                (unsigned long long)release,
                (unsigned long long)start,
                (unsigned long long)finish,
                (unsigned long long)exec_time,
                (unsigned long long)resp_time);

        /* 绝对时间睡眠到下一个 release */
        next_release += period_ns;
        uint64_t now = monotonic_ns();
        if (next_release > now) {
            struct timespec ts = {
                .tv_sec  = (time_t)((next_release - now) / 1000000000ULL),
                .tv_nsec = (long)((next_release - now) % 1000000000ULL),
            };
            clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, NULL);
        } else {
            /* overrun */
            next_release = now;
        }
    }

    int temp_after = read_temp_mC();
    int freq_after = read_cpu_freq_khz(sched_getcpu());
    fprintf(stderr, "# temp_after=%d freq_after=%d\n", temp_after, freq_after);

    if (out != stdout) fclose(out);
    free(buf);
    return 0;
}
