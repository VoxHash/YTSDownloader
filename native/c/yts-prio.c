/*
 * yts-prio — optional nice / idle-I/O priority helper for YTSDownloader.
 * Usage: yts-prio --pid <pid> [--nice N] [--ionice-idle]
 * Prints one JSON line on stdout.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <unistd.h>

#ifdef __linux__
#include <sys/syscall.h>
#ifndef IOPRIO_WHO_PROCESS
#define IOPRIO_WHO_PROCESS 1
#endif
#ifndef IOPRIO_CLASS_IDLE
#define IOPRIO_CLASS_IDLE 3
#endif
#ifndef IOPRIO_PRIO_VALUE
#define IOPRIO_PRIO_VALUE(class, data) (((class) << 13) | (data))
#endif
static int ioprio_set(int which, int who, int ioprio) {
    return (int)syscall(SYS_ioprio_set, which, who, ioprio);
}
#endif

static void die_json(const char *msg) {
    fprintf(stderr, "{\"ok\":false,\"error\":\"%s\"}\n", msg);
    exit(1);
}

int main(int argc, char **argv) {
    long pid = -1;
    int nice_val = 0;
    int have_nice = 0;
    int ionice_idle = 0;
    int i;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--pid") == 0 && i + 1 < argc) {
            pid = strtol(argv[++i], NULL, 10);
        } else if (strcmp(argv[i], "--nice") == 0 && i + 1 < argc) {
            nice_val = (int)strtol(argv[++i], NULL, 10);
            have_nice = 1;
        } else if (strcmp(argv[i], "--ionice-idle") == 0) {
            ionice_idle = 1;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            fputs("yts-prio --pid <pid> [--nice N] [--ionice-idle]\n", stdout);
            return 0;
        } else {
            die_json("unknown argument");
        }
    }
    if (pid <= 0) {
        die_json("required --pid");
    }

    int nice_applied = 0;
    int ionice_applied = 0;
    const char *warn1 = NULL;
    const char *warn2 = NULL;

    if (have_nice) {
        errno = 0;
        if (setpriority(PRIO_PROCESS, (id_t)pid, nice_val) == 0) {
            nice_applied = 1;
        } else {
            warn1 = "setpriority failed";
        }
    }

    if (ionice_idle) {
#ifdef __linux__
        if (ioprio_set(IOPRIO_WHO_PROCESS, (int)pid,
                       IOPRIO_PRIO_VALUE(IOPRIO_CLASS_IDLE, 0)) == 0) {
            ionice_applied = 1;
        } else {
            warn2 = "ioprio_set failed";
        }
#else
        warn2 = "ionice-idle is Linux-only";
#endif
    }

    printf("{\"ok\":true,\"pid\":%ld,\"nice\":", pid);
    if (nice_applied) {
        printf("%d", nice_val);
    } else {
        fputs("null", stdout);
    }
    printf(",\"ionice_idle\":%s,\"warnings\":[",
           ionice_applied ? "true" : "false");
    int first = 1;
    if (warn1) {
        printf("\"%s\"", warn1);
        first = 0;
    }
    if (warn2) {
        if (!first) {
            fputc(',', stdout);
        }
        printf("\"%s\"", warn2);
    }
    fputs("]}\n", stdout);
    return 0;
}
