#include "benchmarks.h"

#include <string.h>

#ifdef USE_OPENMP
#include <omp.h>
#endif

static double checksum_array(const double *x, size_t elements) {
    double sum = 0.0;
#ifdef USE_OPENMP
#pragma omp parallel for reduction(+ : sum)
#endif
    for (size_t i = 0; i < elements; ++i) {
        sum += x[i];
    }
    return sum;
}

double checksum_for_kernel(const char *kernel, const double *a, const double *b,
                           const double *c, const double *d, size_t elements,
                           double measured_checksum) {
    if (strcmp(kernel, "copy") == 0) {
        return checksum_array(b, elements);
    }
    if (strcmp(kernel, "scale") == 0 || strcmp(kernel, "add") == 0) {
        return checksum_array(c, elements);
    }
    if (strcmp(kernel, "triad") == 0) {
        return checksum_array(a, elements);
    }
    if (strcmp(kernel, "stencil1d") == 0) {
        return checksum_array(d, elements);
    }
    return measured_checksum;
}

void initialize_arrays(double *a, double *b, double *c, double *d, size_t elements) {
#ifdef USE_OPENMP
#pragma omp parallel for
#endif
    for (size_t i = 0; i < elements; ++i) {
        a[i] = 1.0 + (double)(i % 97) * 0.001;
        b[i] = 2.0 + (double)(i % 89) * 0.001;
        c[i] = 3.0 + (double)(i % 83) * 0.001;
        d[i] = 0.0;
    }
}

static int kernel_copy(double *a, double *b, size_t elements, benchmark_result *result) {
#ifdef USE_OPENMP
#pragma omp parallel for
#endif
    for (size_t i = 0; i < elements; ++i) {
        b[i] = a[i];
    }
    result->name = "copy";
    result->bytes_per_run = 2 * elements * sizeof(double);
    result->checksum = 0.0;
    return 0;
}

static int kernel_scale(double *b, double *c, size_t elements, benchmark_result *result) {
    const double scalar = 3.0;
#ifdef USE_OPENMP
#pragma omp parallel for
#endif
    for (size_t i = 0; i < elements; ++i) {
        c[i] = scalar * b[i];
    }
    result->name = "scale";
    result->bytes_per_run = 2 * elements * sizeof(double);
    result->checksum = 0.0;
    return 0;
}

static int kernel_add(double *a, double *b, double *c, size_t elements, benchmark_result *result) {
#ifdef USE_OPENMP
#pragma omp parallel for
#endif
    for (size_t i = 0; i < elements; ++i) {
        c[i] = a[i] + b[i];
    }
    result->name = "add";
    result->bytes_per_run = 3 * elements * sizeof(double);
    result->checksum = 0.0;
    return 0;
}

static int kernel_triad(double *a, double *b, double *c, size_t elements, benchmark_result *result) {
    const double scalar = 3.0;
#ifdef USE_OPENMP
#pragma omp parallel for
#endif
    for (size_t i = 0; i < elements; ++i) {
        a[i] = b[i] + scalar * c[i];
    }
    result->name = "triad";
    result->bytes_per_run = 3 * elements * sizeof(double);
    result->checksum = 0.0;
    return 0;
}

static int kernel_sequential(double *a, size_t elements, benchmark_result *result) {
    double sum = 0.0;
    for (size_t i = 0; i < elements; ++i) {
        sum += a[i];
    }
    result->name = "sequential";
    result->bytes_per_run = elements * sizeof(double);
    result->checksum = sum;
    return 0;
}

static int kernel_strided(double *a, size_t elements, size_t stride, benchmark_result *result) {
    if (stride == 0) {
        return 1;
    }
    double sum = 0.0;
    size_t visits = 0;
    for (size_t i = 0; i < elements; i += stride) {
        sum += a[i];
        ++visits;
    }
    result->name = "strided";
    result->bytes_per_run = visits * sizeof(double);
    result->checksum = sum;
    return 0;
}

static int kernel_reduction(double *a, size_t elements, benchmark_result *result) {
    double sum = 0.0;
#ifdef USE_OPENMP
#pragma omp parallel for reduction(+ : sum)
#endif
    for (size_t i = 0; i < elements; ++i) {
        sum += a[i];
    }
    result->name = "reduction";
    result->bytes_per_run = elements * sizeof(double);
    result->checksum = sum;
    return 0;
}

static int kernel_stencil1d(double *a, double *d, size_t elements, benchmark_result *result) {
    if (elements < 3) {
        return 1;
    }
#ifdef USE_OPENMP
#pragma omp parallel for
#endif
    for (size_t i = 1; i < elements - 1; ++i) {
        d[i] = 0.25 * a[i - 1] + 0.5 * a[i] + 0.25 * a[i + 1];
    }
    d[0] = a[0];
    d[elements - 1] = a[elements - 1];
    result->name = "stencil1d";
    result->bytes_per_run = (3 * (elements - 2) + (elements - 2)) * sizeof(double);
    result->checksum = 0.0;
    return 0;
}

int run_kernel(const char *kernel, double *a, double *b, double *c, double *d,
               size_t elements, size_t stride, benchmark_result *result) {
    if (strcmp(kernel, "copy") == 0) {
        return kernel_copy(a, b, elements, result);
    }
    if (strcmp(kernel, "scale") == 0) {
        return kernel_scale(b, c, elements, result);
    }
    if (strcmp(kernel, "add") == 0) {
        return kernel_add(a, b, c, elements, result);
    }
    if (strcmp(kernel, "triad") == 0) {
        return kernel_triad(a, b, c, elements, result);
    }
    if (strcmp(kernel, "sequential") == 0) {
        return kernel_sequential(a, elements, result);
    }
    if (strcmp(kernel, "strided") == 0) {
        return kernel_strided(a, elements, stride, result);
    }
    if (strcmp(kernel, "reduction") == 0) {
        return kernel_reduction(a, elements, result);
    }
    if (strcmp(kernel, "stencil1d") == 0) {
        return kernel_stencil1d(a, d, elements, result);
    }
    return 1;
}
