# C++ 并发专题

这份文档按 flash card 结构整理 C++ 并发高频主题。回答时先讲正确性：共享状态、同步关系、生命周期和退出协议；再讲性能和现代替代方案。

## 1. 并发学习的总主线

### 核心答案

并发题的主线不是 API，而是共享可变状态、同步边界、可见性和退出协议。先证明正确性，再讨论性能。

### English explanation

In an English interview, I would answer it like this:

Concurrency is mainly about shared mutable state, synchronization boundaries, visibility, and shutdown. API names are secondary to proving correctness.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <mutex>

struct Counter {
    void add() {
        std::lock_guard<std::mutex> lock(m);
        ++value;
    }

    int get() const {
        std::lock_guard<std::mutex> lock(m);
        return value;
    }

    mutable std::mutex m;
    int value = 0;
};
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 2. 线程 vs 进程

### 核心答案

线程共享同一进程地址空间，通信低成本但同步复杂；进程隔离更强，故障边界更清楚，但通信和切换成本通常更高。

### English explanation

In an English interview, I would answer it like this:

Threads share an address space and are cheaper to communicate between, while processes provide stronger isolation at a higher communication cost.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <thread>

int shared_counter = 0;

void worker() {
    ++shared_counter; // 多线程共享地址空间，真实代码必须同步
}

int main() {
    std::thread t(worker);
    t.join();
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 3. `std::thread`

### 核心答案

`std::thread` 是直接线程抽象，创建后必须管理生命周期；joinable 的 thread 析构会调用 `std::terminate`。

### English explanation

In an English interview, I would answer it like this:

`std::thread` directly represents a thread of execution, and its lifetime must be explicitly managed with join or detach.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <iostream>
#include <thread>

void worker() {
    std::cout << "worker\n";
}

int main() {
    std::thread t(worker);
    t.join();
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 4. `join()` vs `detach()`

### 核心答案

`join()` 等待线程结束，生命周期可推导；`detach()` 让线程脱离管理，必须自己证明它访问的对象仍然存活。

### English explanation

In an English interview, I would answer it like this:

`join` makes the current thread wait and keeps lifetime reasoning clear; `detach` removes ownership and makes lifetime much harder to prove.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <thread>

void work() {}

int main() {
    std::thread t(work);
    t.join(); // 优先选择可管理的收尾
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 5. 竞态条件（race condition）

### 核心答案

多个线程访问同一共享状态，至少一个写入，且缺少同步，就可能发生竞态条件；在 C++ 中数据竞争是未定义行为。

### English explanation

In an English interview, I would answer it like this:

A race condition appears when timing affects correctness; in C++, an unsynchronized data race is undefined behavior.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <mutex>
#include <thread>

int counter = 0;
std::mutex m;

void add() {
    for (int i = 0; i < 1000; ++i) {
        std::lock_guard<std::mutex> lock(m);
        ++counter;
    }
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 6. `std::mutex`

### 核心答案

`std::mutex` 用互斥保护临界区，让同一时间只有一个线程访问共享可变状态；它保护的是不变量，不只是某一行代码。

### English explanation

In an English interview, I would answer it like this:

`std::mutex` protects a critical section so only one thread can access shared mutable state at a time.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <mutex>
#include <vector>

class Queue {
public:
    void push(int v) {
        std::lock_guard<std::mutex> lock(m_);
        data_.push_back(v);
    }
private:
    std::mutex m_;
    std::vector<int> data_;
};
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 7. `std::lock_guard` vs `std::unique_lock`

### 核心答案

`lock_guard` 是简单 RAII 锁，适合固定作用域；`unique_lock` 更灵活，支持延迟加锁、提前解锁和条件变量。

### English explanation

In an English interview, I would answer it like this:

`lock_guard` is a simple scoped lock, while `unique_lock` is more flexible and works with condition variables.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <condition_variable>
#include <mutex>

std::mutex m;
std::condition_variable cv;
bool ready = false;

void waitReady() {
    std::unique_lock<std::mutex> lock(m);
    cv.wait(lock, [] { return ready; });
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 8. 条件变量 `std::condition_variable`

### 核心答案

条件变量用于“等待某个条件成立”，必须和互斥锁、谓词一起使用，避免虚假唤醒和错过通知。

### English explanation

In an English interview, I would answer it like this:

A condition variable blocks until a condition may be true; the real condition must be checked under a mutex with a predicate.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <condition_variable>
#include <mutex>
#include <queue>

std::mutex m;
std::condition_variable cv;
std::queue<int> q;

int pop() {
    std::unique_lock<std::mutex> lock(m);
    cv.wait(lock, [] { return !q.empty(); });
    int v = q.front();
    q.pop();
    return v;
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 9. `std::atomic`

### 核心答案

`std::atomic` 让单个对象的读写或读改写操作具备原子性；它不自动保护多个变量组成的不变量。

### English explanation

In an English interview, I would answer it like this:

`std::atomic` provides atomic operations on one object, but it does not automatically protect multi-variable invariants.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <atomic>

std::atomic<int> counter{0};

void add() {
    counter.fetch_add(1, std::memory_order_relaxed);
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 10. `atomic` 和 `mutex` 的边界

### 核心答案

单个计数器、标志位可优先考虑 atomic；多个字段的一致性、容器操作和复杂状态机通常应使用 mutex。

### English explanation

In an English interview, I would answer it like this:

Use atomics for small independent state, and mutexes when an invariant spans multiple fields or operations.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <mutex>
#include <string>

struct UserState {
    std::mutex m;
    std::string name;
    int score = 0;

    void update(std::string n, int s) {
        std::lock_guard<std::mutex> lock(m);
        name = std::move(n);
        score = s;
    }
};
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 11. `volatile` 为什么不等于线程安全

### 核心答案

`volatile` 不提供原子性、互斥或线程间同步；C++ 并发应使用 atomic、mutex、condition_variable 等同步工具。

### English explanation

In an English interview, I would answer it like this:

`volatile` does not provide atomicity, mutual exclusion, or inter-thread synchronization in C++.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <atomic>

std::atomic<bool> stop{false};

void requestStop() {
    stop.store(true, std::memory_order_release);
}

bool shouldStop() {
    return stop.load(std::memory_order_acquire);
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 12. C++ 内存模型

### 核心答案

C++ 内存模型定义线程间可见性、happens-before、数据竞争和合法重排序，是判断原子代码是否正确的基础。

### English explanation

In an English interview, I would answer it like this:

The C++ memory model defines visibility, happens-before relationships, data races, and legal reordering between threads.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <atomic>
#include <thread>

std::atomic<bool> ready{false};
int payload = 0;

void producer() {
    payload = 42;
    ready.store(true, std::memory_order_release);
}

void consumer() {
    while (!ready.load(std::memory_order_acquire)) {}
    int value = payload;
    (void)value;
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 13. `memory_order`

### 核心答案

内存序控制原子操作的可见性和重排序约束：`relaxed` 只保原子性，release/acquire 建立发布获取关系，`seq_cst` 最直观但约束更强。

### English explanation

In an English interview, I would answer it like this:

Memory ordering controls visibility and reordering constraints for atomic operations.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <atomic>

std::atomic<int> count{0};
std::atomic<bool> ready{false};
int data = 0;

void publish() {
    data = 7;
    ready.store(true, std::memory_order_release);
    count.fetch_add(1, std::memory_order_relaxed);
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 14. 线程池

### 核心答案

线程池通过复用固定数量工作线程处理大量任务，核心是任务队列、互斥锁、条件变量、停止标志和清晰关闭协议。

### English explanation

In an English interview, I would answer it like this:

A thread pool reuses worker threads to execute many tasks and needs a queue, synchronization, and a shutdown protocol.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <condition_variable>
#include <functional>
#include <mutex>
#include <queue>

std::mutex m;
std::condition_variable cv;
std::queue<std::function<void()>> tasks;
bool stop = false;

void workerLoop() {
    while (true) {
        std::function<void()> task;
        {
            std::unique_lock<std::mutex> lock(m);
            cv.wait(lock, [] { return stop || !tasks.empty(); });
            if (stop && tasks.empty()) return;
            task = std::move(tasks.front());
            tasks.pop();
        }
        task();
    }
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 15. `std::future` / `std::async`

### 核心答案

`future/async` 表达异步任务和未来结果，比裸线程更关注结果交付；但调度策略、异常传播和任务生命周期仍要理解。

### English explanation

In an English interview, I would answer it like this:

`future` and `async` model asynchronous results rather than raw thread ownership.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <future>
#include <iostream>

int main() {
    auto fut = std::async(std::launch::async, [] { return 42; });
    std::cout << fut.get() << '
';
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 16. 并发面试里的常见错误表达

### 核心答案

并发面试最怕绝对化表达，例如“多线程一定更快”“atomic 就够了”“lock-free 一定高级”。正确回答要先讲可证明正确性。

### English explanation

In an English interview, I would answer it like this:

Good concurrency answers avoid absolute claims and start from correctness, synchronization, and lifetime reasoning.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <mutex>

// 好表达：先保护共享状态，再谈性能。
std::mutex m;
int value = 0;

void setValue(int v) {
    std::lock_guard<std::mutex> lock(m);
    value = v;
}
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---

## 17. 复习建议

### 核心答案

并发复习顺序应是共享状态、锁、条件变量、线程池，再到 atomic、内存模型和 lock-free；任何题都先回答正确性，再回答性能。

### English explanation

In an English interview, I would answer it like this:

Study concurrency from shared state and locks first, then condition variables, pools, atomics, and memory ordering.

### 错误回答示例

- “只背 API 名字，不说明同步关系或生命周期”
- “能跑几次就说明线程安全”
- “性能一定比可证明正确性更重要”

### 面试官想听什么

- 你是否能说清共享状态、同步边界和可见性关系
- 你是否知道工具的适用场景和失败模式
- 你是否能把代码例子和工程取舍联系起来

### 项目里怎么说

项目里我会先证明同步关系正确，再考虑性能优化；优先使用更容易维护的锁、RAII 和高层抽象，只有在 profiling 证明瓶颈后才下沉到更复杂的 atomic 或弱内存序。

### 深入解释

- 并发 bug 往往来自共享可变状态、生命周期失控或错误的可见性假设
- 锁适合保护复合不变量，atomic 适合小而独立的状态
- 条件变量必须围绕谓词和互斥锁设计，线程池必须有关闭协议
- 现代替代方案包括 `std::jthread`、RAII 锁、任务队列和更明确的所有权模型

### 示例

```cpp
#include <atomic>
#include <mutex>

// 复习主线：简单状态可 atomic，复合不变量用 mutex。
std::atomic<int> counter{0};
std::mutex state_mutex;
```

### 代码讲解

- 示例重点展示这个工具解决的同步或生命周期问题
- 面试时要指出哪一行建立了互斥、等待、原子性或可见性关系
- 不要只说 API 名字，要解释它保护了什么共享状态
- 如果需求变复杂，应优先考虑更高层、更容易证明正确的抽象

### 面试追问

- 这里的数据竞争或生命周期风险在哪里？
- 如果任务量变大，应该用裸线程、线程池还是异步结果模型？
- 这段代码的退出协议和异常路径是否清楚？

---
