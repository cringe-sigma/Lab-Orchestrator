/*
 * InterAgent Demo — Cache Attacker
 *
 * 反复访问指定大小内存区域，持续制造 cache 干扰
 *
 * 用法:
 *   taskset -c <cpu> ./cache_attacker <working_set_kib> <access_pattern> <duration_s>
 *
 * access_pattern: seq | rand
 */
#include "common.h"
#include <signal.h>

static volatile int running = 1;
static void sig_handler(int sig) { running = 0; }

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: cache_attacker <working_set_kib> <seq|rand> <duration_s>\n");
        return 1;
    }

    size_t work_kib    = (size_t)atol(argv[1]);
    const char *pattern = argv[2];
    int    duration_s  = atoi(argv[3]);

    int use_random = (strcmp(pattern, "rand") == 0);

    size_t work_bytes = work_kib * 1024;
    char *buf = (char *)malloc(work_bytes);
    if (!buf) { perror("malloc"); return 1; }
    memset(buf, 0xBB, work_bytes);

    size_t stride = 64;
    unsigned int seed = 42;

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    fprintf(stderr, "# cache_attacker: %zuKiB %s %ds on CPU%d\n",
            work_kib, pattern, duration_s, sched_getcpu());

    uint64_t deadline = monotonic_ns() + (uint64_t)duration_s * 1000000000ULL;

    while (running && monotonic_ns() < deadline) {
        if (use_random) {
            touch_memory_random(buf, work_bytes, stride, &seed);
        } else {
            touch_memory_sequential(buf, work_bytes, stride);
        }
    }

    free(buf);
    fprintf(stderr, "# cache_attacker done\n");
    return 0;
}
