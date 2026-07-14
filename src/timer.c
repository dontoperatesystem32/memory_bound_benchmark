#define _POSIX_C_SOURCE 200112L

#include "timer.h"

#include <time.h>

double monotonic_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1.0e-9;
}
