#ifndef BENCHMARKS_H
#define BENCHMARKS_H

#include <stddef.h>

typedef struct {
    const char *name;
    size_t bytes_per_run;
    double checksum;
} benchmark_result;

int run_kernel(const char *kernel, double *a, double *b, double *c, double *d,
               size_t elements, size_t stride, benchmark_result *result);

void initialize_arrays(double *a, double *b, double *c, double *d, size_t elements);

double checksum_for_kernel(const char *kernel, const double *a, const double *b,
                           const double *c, const double *d, size_t elements,
                           double measured_checksum);

#endif
