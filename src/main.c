#define _POSIX_C_SOURCE 200112L

#include "benchmarks.h"
#include "timer.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef USE_OPENMP
#include <omp.h>
#endif

#ifndef COMPILER_ID
#if defined(__clang__)
#define COMPILER_ID "clang " __clang_version__
#elif defined(__GNUC__)
#define COMPILER_ID "gcc " __VERSION__
#else
#define COMPILER_ID "unknown"
#endif
#endif

#ifndef COMPILER_FLAGS
#define COMPILER_FLAGS "recorded_in_build_log_or_metadata"
#endif

typedef struct {
    const char *machine_id;
    const char *kernel;
    const char *csv_path;
    const char *source_benchmark;
    size_t elements;
    size_t stride;
    int threads;
    int repetitions;
    int iterations;
    int warmups;
} options;

static void usage(const char *argv0) {
    fprintf(stderr,
            "Usage: %s --machine-id ID --kernel NAME --elements N [options]\n"
            "\n"
            "Options:\n"
            "  --csv PATH                 CSV output path; default stdout\n"
            "  --source-benchmark NAME    source label; default custom\n"
            "  --stride N                 stride for strided kernel; default 1\n"
            "  --threads N                requested OpenMP threads; default 1\n"
            "  --repetitions N            repetitions; default 3\n"
            "  --iterations N             kernel calls per timed repetition; default 1\n"
            "  --warmups N                untimed kernel calls before timing; default 1\n"
            "  --help                     show this help\n"
            "\n"
            "Kernels: copy, scale, add, triad, sequential, strided, reduction, stencil1d\n",
            argv0);
}

static int parse_size(const char *text, size_t *out) {
    errno = 0;
    char *end = NULL;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value == 0) {
        return 1;
    }
    *out = (size_t)value;
    return 0;
}

static int parse_int(const char *text, int *out) {
    errno = 0;
    char *end = NULL;
    long value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value <= 0) {
        return 1;
    }
    *out = (int)value;
    return 0;
}

static int parse_args(int argc, char **argv, options *opts) {
    opts->machine_id = "unknown";
    opts->kernel = NULL;
    opts->csv_path = NULL;
    opts->source_benchmark = "custom";
    opts->elements = 0;
    opts->stride = 1;
    opts->threads = 1;
    opts->repetitions = 3;
    opts->iterations = 1;
    opts->warmups = 1;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            exit(0);
        } else if (strcmp(argv[i], "--machine-id") == 0 && i + 1 < argc) {
            opts->machine_id = argv[++i];
        } else if (strcmp(argv[i], "--kernel") == 0 && i + 1 < argc) {
            opts->kernel = argv[++i];
        } else if (strcmp(argv[i], "--csv") == 0 && i + 1 < argc) {
            opts->csv_path = argv[++i];
        } else if (strcmp(argv[i], "--source-benchmark") == 0 && i + 1 < argc) {
            opts->source_benchmark = argv[++i];
        } else if (strcmp(argv[i], "--elements") == 0 && i + 1 < argc) {
            if (parse_size(argv[++i], &opts->elements) != 0) {
                return 1;
            }
        } else if (strcmp(argv[i], "--stride") == 0 && i + 1 < argc) {
            if (parse_size(argv[++i], &opts->stride) != 0) {
                return 1;
            }
        } else if (strcmp(argv[i], "--threads") == 0 && i + 1 < argc) {
            if (parse_int(argv[++i], &opts->threads) != 0) {
                return 1;
            }
        } else if (strcmp(argv[i], "--repetitions") == 0 && i + 1 < argc) {
            if (parse_int(argv[++i], &opts->repetitions) != 0) {
                return 1;
            }
        } else if (strcmp(argv[i], "--iterations") == 0 && i + 1 < argc) {
            if (parse_int(argv[++i], &opts->iterations) != 0) {
                return 1;
            }
        } else if (strcmp(argv[i], "--warmups") == 0 && i + 1 < argc) {
            if (parse_int(argv[++i], &opts->warmups) != 0) {
                return 1;
            }
        } else {
            return 1;
        }
    }

    return opts->kernel == NULL || opts->elements == 0;
}

static int allocate_arrays(size_t elements, double **a, double **b, double **c, double **d) {
    const size_t bytes = elements * sizeof(double);
    *a = NULL;
    *b = NULL;
    *c = NULL;
    *d = NULL;
    if (posix_memalign((void **)a, 64, bytes) != 0) {
        return 1;
    }
    if (posix_memalign((void **)b, 64, bytes) != 0) {
        return 1;
    }
    if (posix_memalign((void **)c, 64, bytes) != 0) {
        return 1;
    }
    if (posix_memalign((void **)d, 64, bytes) != 0) {
        return 1;
    }
    return 0;
}

static int file_exists_and_nonempty(const char *path) {
    FILE *f = fopen(path, "r");
    if (f == NULL) {
        return 0;
    }
    int ch = fgetc(f);
    fclose(f);
    return ch != EOF;
}

static FILE *open_csv(const char *path, int *needs_header) {
    if (path == NULL) {
        *needs_header = 1;
        return stdout;
    }
    *needs_header = !file_exists_and_nonempty(path);
    return fopen(path, "a");
}

int main(int argc, char **argv) {
    options opts;
    if (parse_args(argc, argv, &opts) != 0) {
        usage(argv[0]);
        return 2;
    }

#ifdef USE_OPENMP
    omp_set_dynamic(0);
    omp_set_num_threads(opts.threads);
#else
    if (opts.threads != 1) {
        fprintf(stderr, "This executable was built without OpenMP; use --threads 1 or rebuild with `make openmp`.\n");
        return 2;
    }
#endif

    double *a = NULL;
    double *b = NULL;
    double *c = NULL;
    double *d = NULL;
    if (allocate_arrays(opts.elements, &a, &b, &c, &d) != 0) {
        fprintf(stderr, "Failed to allocate arrays for %zu elements\n", opts.elements);
        free(a);
        free(b);
        free(c);
        free(d);
        return 1;
    }

    int needs_header = 0;
    FILE *csv = open_csv(opts.csv_path, &needs_header);
    if (csv == NULL) {
        fprintf(stderr, "Failed to open CSV output: %s\n", opts.csv_path);
        free(a);
        free(b);
        free(c);
        free(d);
        return 1;
    }

    if (needs_header) {
        fprintf(csv, "source_benchmark,machine_id,kernel,elements,bytes,stride,threads,repetition,warmups,iterations,runtime_sec,bandwidth_gbps,checksum,compiler,compiler_flags\n");
    }

    for (int rep = 1; rep <= opts.repetitions; ++rep) {
        initialize_arrays(a, b, c, d, opts.elements);

        benchmark_result result = {0};
        for (int warmup = 0; warmup < opts.warmups; ++warmup) {
            if (run_kernel(opts.kernel, a, b, c, d, opts.elements, opts.stride, &result) != 0) {
                fprintf(stderr, "Unknown or invalid kernel: %s\n", opts.kernel);
                if (csv != stdout) {
                    fclose(csv);
                }
                free(a);
                free(b);
                free(c);
                free(d);
                return 2;
            }
        }
        double start = monotonic_seconds();
        for (int iteration = 0; iteration < opts.iterations; ++iteration) {
            if (run_kernel(opts.kernel, a, b, c, d, opts.elements, opts.stride, &result) != 0) {
                fprintf(stderr, "Unknown or invalid kernel: %s\n", opts.kernel);
                if (csv != stdout) {
                    fclose(csv);
                }
                free(a);
                free(b);
                free(c);
                free(d);
                return 2;
            }
        }
        double elapsed = monotonic_seconds() - start;
        result.checksum = checksum_for_kernel(result.name, a, b, c, d, opts.elements, result.checksum);
        if (result.bytes_per_run > SIZE_MAX / (size_t)opts.iterations) {
            fprintf(stderr, "Byte count overflow for requested iteration count\n");
            if (csv != stdout) {
                fclose(csv);
            }
            free(a);
            free(b);
            free(c);
            free(d);
            return 1;
        }
        size_t total_bytes = result.bytes_per_run * (size_t)opts.iterations;
        double bandwidth_gbps = ((double)total_bytes / elapsed) / 1.0e9;

        fprintf(csv, "%s,%s,%s,%zu,%zu,%zu,%d,%d,%d,%d,%.9f,%.6f,%.17g,%s,%s\n",
                opts.source_benchmark, opts.machine_id, result.name, opts.elements,
                total_bytes, opts.stride, opts.threads, rep, opts.warmups, opts.iterations, elapsed,
                bandwidth_gbps, result.checksum, COMPILER_ID, COMPILER_FLAGS);
        fflush(csv);
    }

    if (csv != stdout) {
        fclose(csv);
    }
    free(a);
    free(b);
    free(c);
    free(d);
    return 0;
}
