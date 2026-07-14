CC ?= clang
BUILD_DIR := build
BIN_DIR := bin
TARGET := $(BIN_DIR)/membench

CPPFLAGS ?= -Iinclude
CFLAGS ?= -O3 -std=c11 -Wall -Wextra -pedantic
LDFLAGS ?=
LDLIBS ?=

SOURCES := src/main.c src/benchmarks.c src/timer.c
OBJECTS := $(SOURCES:src/%.c=$(BUILD_DIR)/%.o)

.PHONY: all clean openmp dirs

all: $(TARGET)

openmp: CPPFLAGS += -DUSE_OPENMP
openmp: CFLAGS += -fopenmp
openmp: LDLIBS += -fopenmp
openmp: $(TARGET)

$(TARGET): $(OBJECTS) | dirs
	$(CC) $(LDFLAGS) $(OBJECTS) $(LDLIBS) -o $@

$(BUILD_DIR)/%.o: src/%.c | dirs
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

dirs:
	mkdir -p $(BUILD_DIR) $(BIN_DIR)

clean:
	rm -rf $(BUILD_DIR) $(BIN_DIR)

