# C++ Interview Lab Cheatsheet

## CMake Build Flow

| Command | Stage | Compiles? | Notes |
|---|---|---|---|
| `cmake .` | Configure (in-source) | ✗ | Pollutes source tree — avoid |
| `cmake -B build` | Configure (out-of-source) | ✗ | Modern, preferred |
| `cmake --build build` | Build/Compile | ✓ | Build-tool agnostic |
| `cmake -S src -B build` | Configure (explicit dirs) | ✗ | Most explicit form |

### Quick Commands

```bash
# ✅ Out-of-source build (standard flow)
cmake -B build && cmake --build build

# 🧹 Clean rebuild
rm -rf build && cmake -B build && cmake --build build

# 🔧 Build type
cmake -B build -DCMAKE_BUILD_TYPE=Release

# ⚡ Parallel (Ninja)
cmake -B build -G Ninja && cmake --build build

# 📦 Install
cmake --build build && cmake --install build
```

> **Key**: `cmake .` generates in-place (legacy); `cmake -B <dir>` generates into `<dir>` (modern); `cmake --build <dir>` runs make/ninja inside `<dir>`.

---

## CMakeLists.txt Templates

### Full Skeleton

```cmake
cmake_minimum_required(VERSION 3.16)
project(my_project LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(my_app
    src/main.cpp
    src/foo.cpp
)

target_include_directories(my_app
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(my_app
    PRIVATE -Wall -Wextra -Wpedantic
)

find_package(Threads REQUIRED)
target_link_libraries(my_app PRIVATE Threads::Threads)
```

### Minimal Target (single-file project)

```cmake
cmake_minimum_required(VERSION 3.16)
project(my_project)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(my_app src/main.cpp)

target_include_directories(my_app
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include
)
```

### Quick Lookup

| Need | CMake Command |
|---|---|
| Minimum version | `cmake_minimum_required(...)` |
| Project name | `project(name LANGUAGES CXX)` |
| C++ standard | `set(CMAKE_CXX_STANDARD 17)` |
| Build executable | `add_executable(app src/main.cpp)` |
| Header search path | `target_include_directories(app PRIVATE include)` |
| Warnings | `target_compile_options(app PRIVATE -Wall -Wextra -Wpedantic)` |
| Threads | `find_package(Threads REQUIRED)` + `target_link_libraries(app PRIVATE Threads::Threads)` |

### When to Use `target_compile_options`

| Scenario | Use `target_compile_options`? |
|---|---|
| C++ standard | No — `CMAKE_CXX_STANDARD` handles it |
| Header search path | No — `target_include_directories` handles it |
| Warnings (`-Wall -Wextra`) | **Yes** |
| Optimization (`-O2`) | Only if overriding defaults |
| Platform/compiler-specific flags | **Yes** |

> **Short rule**: C++ standard → `CMAKE_CXX_STANDARD`; Header path → `target_include_directories`; Extra flags → `target_compile_options`.

---

## CMake PRIVATE / INTERFACE / PUBLIC

Dependency chain: `A → B → C` (A depends on B, B depends on C)

| Keyword | Self needs? | Consumer gets? | Use case |
|---|---|---|---|
| `PRIVATE` | ✓ | ✗ | Internal impl — not exposed in headers |
| `INTERFACE` | ✗ | ✓ | Header-only lib — consumers need this |
| `PUBLIC` | ✓ | ✓ | Both self and consumers need it |

### Example

```cmake
# C: internal math, not exposed
target_include_directories(C PRIVATE include/C)

# B: uses C, exposes public API
target_link_libraries(B PUBLIC C)
target_include_directories(B
    PUBLIC  include/B        # A also sees this
    PRIVATE src/B_internal   # Only B sees this
)

# A: final app
target_link_libraries(A PRIVATE B)  # Gets B + C transitively
```

### Visibility

| Target | `include/C` | `include/B` | `src/B_internal` |
|---|---|---|---|
| C | ✓ | ✗ | ✗ |
| B | ✓ (via C) | ✓ | ✓ |
| A | ✗ | ✓ (via B.PUBLIC) | ✗ |

---

## CTest / Testing

### Minimal Setup

```cmake
enable_testing()

add_executable(my_test tests/my_test.cpp)

target_include_directories(my_test
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_test(NAME my_test COMMAND my_test)
```

| Command | Meaning |
|---|---|
| `enable_testing()` | Turn on CTest support |
| `add_executable(my_test ...)` | Compile the test binary |
| `add_test(NAME ... COMMAND ...)` | Register the test with CTest |

### Common Commands

```bash
ctest --test-dir build                          # Run all tests (PASS/FAIL summary)
ctest --test-dir build --output-on-failure      # + show output of failed tests
ctest --test-dir build --output-on-failure --stop-on-failure  # Stop on first failure
ctest --test-dir build -R "ThreadSafe"          # Run tests matching regex
ctest --test-dir build --repeat-until-fail 10   # Stress-test (repeat N times)
ctest --test-dir build -V                       # Verbose: show every test
ctest --test-dir build -j 4                     # Parallel execution
```

### `--output-on-failure` Explained

| Behavior | Default | `--output-on-failure` | `-V` |
|---|---|---|---|
| PASS test output | Discarded | Discarded | **Printed** |
| FAIL test output | Discarded | **Printed** | **Printed** |
| Test name shown | ✓ | ✓ | ✓ |
| Best for | All passing | CI / daily dev | Debugging |

CTest's design: **silent by default, speak only on failure**. Output of passing tests is captured but discarded to keep logs clean. `--output-on-failure` dumps captured output only when a test fails. Use `-V` when you need to see everything.

---

## C++ Lambda Capture

### Core Concept

Default lambda `operator()` is `const`:

```cpp
void operator()() const;
```

Implications:
- `[=]` captures locals **by value** (internal copies); can't modify by default
- `[&]` captures locals **by reference**; can modify external variables
- `[this]` captures object pointer; can modify members through pointer
- In member functions, `[=]` implicitly captures `this` — members are accessed via pointer, NOT by value copy

### Three Capture Modes

```cpp
int local = 10;
```

#### `[this]` — object pointer only

```cpp
auto lam = [this] {
    queue_.push(5);       // ✅ modifies member via this->queue_
    // local = 20;        // ❌ 'local' not captured
};
```

#### `[&]` — all by reference

```cpp
auto lam = [&] {
    queue_.push(5);       // ✅ via this
    local = 20;           // ✅ modifies external local
};
```

#### `[=]` — all by value

```cpp
auto lam = [=] {
    queue_.push(5);       // ✅ via this pointer (not a copy!)
    // local = 20;        // ❌ copy is const
};
```

**Why `[=]` can modify `queue_` but not `local`:**

| Object | Accessed via | Modifiable? |
|---|---|---|
| `local` | Lambda's internal copy | No (protected by `const operator()`) |
| `queue_` | `this->queue_` pointer | Yes (pointed-to object not const) |

```cpp
// Approximate mental model:
MyClass* const this_ptr;      // pointer itself is const
this_ptr->queue_.push(5);     // pointed-to object is NOT const → can modify
```

### `mutable` — Allow Modifying Value Captures

```cpp
int local = 10;

auto lam = [=]() mutable {
    local = 20;   // modifies internal copy only
};

lam();
// External local is still 10
```

### Common Mistakes

```cpp
// ❌ Wrong: using class member in lambda without [this]
cv_.wait(lock, [] {
    return !queue_.empty();   // error: 'this' not captured
});

// ✅ Correct
cv_.wait(lock, [this] {
    return shutdown_ || !queue_.empty();
});
```

> **Error clue**: `'this' was not captured for this lambda function`

### C++20 Recommended Syntax

```cpp
auto lam1 = [this] {              // Explicit this capture
    queue_.push(5);
};

auto lam2 = [=, this] {           // Value-capture locals, explicit this
    queue_.push(5);
    std::cout << local << '\n';
};

auto lam3 = [*this] {             // Copy of *this (C++17+)
    // uses a snapshot of current object
};
```

### Summary

```
[=]     locals by value (const), members via this (modifiable)
[&]     locals by ref, members via this (both modifiable)
[this]  object pointer only, members modifiable
mutable allows modifying value-captured copies (original unchanged)
```

---

## Constructor / Destructor Syntax

```cpp
class Foo {
public:
    Foo() = default;   // ✅ constructor — no return type
    ~Foo() = default;  // ✅ destructor — no return type
};
```

```cpp
// ❌ Common mistake:
void Foo() = default;   // Error: constructor has no return type
void ~Foo() = default;  // Error: destructor has no return type
```

> **Error clue**: `return type specification for constructor invalid`

---

## lock_guard vs unique_lock

| Tool | Best for | Manual unlock? | Works with `cv::wait`? |
|---|---|---|---|
| `std::lock_guard<std::mutex>` | Simple critical section | No | No |
| `std::unique_lock<std::mutex>` | Condition variable / flexible locking | Yes | **Yes** |

### Use `lock_guard` for simple push

```cpp
void push(T item) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push(std::move(item));
    }
    cv_.notify_one();
}
```

### Use `unique_lock` for conditional wait

```cpp
bool wait_and_pop(T& item) {
    std::unique_lock<std::mutex> lock(mutex_);

    cv_.wait(lock, [this] {
        return shutdown_ || !queue_.empty();
    });

    if (queue_.empty()) return false;

    item = std::move(queue_.front());
    queue_.pop();
    return true;
}
```

> **Rule**: Short critical section → `lock_guard`; need `wait`/unlock/relock → `unique_lock`.

### Move-Before-Pop Pattern

```cpp
item = std::move(queue_.front());  // Take ownership of resources
queue_.pop();                      // Destroy the (now moved-from) element
```

| Operation | Copy | Move |
|---|---|---|
| Syntax | `item = queue_.front()` | `item = std::move(queue_.front())` |

**Why**: Avoids copies for large/move-only types (e.g., `std::unique_ptr<T>`). The front element is about to be destroyed anyway. Note: `std::move` only casts to rvalue — the actual move happens in the assignment/constructor.

---

## ThreadSafeQueue Checklist

### Required Headers
```cpp
#include <condition_variable>
#include <mutex>
#include <queue>
```

### Required Members
```cpp
mutable std::mutex mutex_;
std::condition_variable cv_;
std::queue<T> queue_;
bool shutdown_ = false;
```

### Required Methods
```cpp
void push(T item);
bool wait_and_pop(T& item);
void shutdown();
```

### Key Patterns

```cpp
// ✅ Correct wait predicate
cv_.wait(lock, [this] {
    return shutdown_ || !queue_.empty();
});

// ✅ Correct consumer loop
int value = 0;
while (queue.wait_and_pop(value)) {
    // process value
}

// ❌ Avoid — race-prone in multi-threaded code
while (!queue.empty()) { ... }
```

### Why `mutable std::mutex`

```cpp
bool empty() const {
    std::lock_guard<std::mutex> lock(mutex_);  // lock() modifies mutex state
    return queue_.empty();
}
```

- `empty()` is `const` → promises not to change logical state
- `lock(mutex_)` changes the mutex's *internal* lock state
- `mutable` allows const methods to lock the mutex

> **Rule**: const read function + needs mutex lock → `mutable std::mutex`

---

## Common Error Messages

| Error | Likely Cause | Fix |
|---|---|---|
| `return type specification for constructor invalid` | Wrote `void ClassName()` | Remove `void` |
| `'this' was not captured for this lambda function` | Lambda uses member without capture | Use `[this]` |
| `has no member named 'empty'` | Called `queue.empty()` but no such method | Add `empty()` or use `wait_and_pop()` loop |
| `No tests were found!!!` | Wrong directory or unregistered tests | `cd build && ctest`, check `enable_testing()` + `add_test()` |
| Undefined reference to pthread symbols | Threads not linked | `find_package(Threads REQUIRED)` + `target_link_libraries(... Threads::Threads)` |