/*
 * InterAgent Demo — Memory Attacker
 *
 * 持续读/写/复制较大内存区域，制造 DRAM bandwidth 干扰
 *
 * 用法:
 *   taskset -c <cpu> ./memory_attacker <working_set_mib> <read|write|copy> <duration_s>
 */
#include "common.h"
#include <signal.h>

static volatile int running = 1;
static void sig_handler(int sig) { running = 0; }

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: memory_attacker <working_set_mib> <read|write|copy> <duration_s>\n");
        return 1;
    }

    size_t work_mib    = (size_t)atol(argv[1]);
    const char *op     = argv[2];
    int    duration_s  = atoi(argv[3]);

    size_t work_bytes = work_mib * 1024 * 1024;
    char *buf1 = (char *)malloc(work_bytes);
    char *buf2 = NULL;

    if (!buf1) { perror("malloc buf1"); return 1; }
    memset(buf1, 0xCC, work_bytes);

    if (strcmp(op, "copy") == 0) {
        buf2 = (char *)malloc(work_bytes);
        if (!buf2) { perror("malloc buf2"); free(buf1); return 1; }
        memset(buf2, 0xDD, work_bytes);
    }

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    fprintf(stderr, "# memory_attacker: %zuMiB %s %ds on CPU%d\n",
            work_mib, op, duration_s, sched_getcpu());

    uint64_t deadline = monotonic_ns() + (uint64_t)duration_s * 1000000000ULL;

    while (running && monotonic_ns() < deadline) {
        if (strcmp(op, "read") == 0) {
            /* 读: 触发读带宽 */
            volatile char *p = (volatile char *)buf1;
            for (size_t i = 0; i < work_bytes; i += 64) {
                volatile char x = p[i]; (void)x;
            }
        } else if (strcmp(op, "write") == 0) {
            /* 写: memset 触发写带宽 */
            memset(buf1, (char)(monotonic_ns() & 0xFF), work_bytes);
        } else if (strcmp(op, "copy") == 0 && buf2) {
            /* copy: memcpy */
            memcpy(buf2, buf1, work_bytes);
            /* 交换方向 */
            char *tmp = buf1; buf1 = buf2; buf2 = tmp;
        }
    }

    free(buf1);
    free(buf2);
    fprintf(stderr, "# memory_attacker done\n");
    return 0;
}
