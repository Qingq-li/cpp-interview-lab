# C++ 并发专题

这份文档专门整理并发相关高频主题，目标不是只背定义，而是把这些问题真正串起来：

- 为什么会出问题
- 哪个工具解决什么问题
- 什么时候该用，什么时候不该用
- 示例代码里该看哪一行

---

## 1. 并发学习的总主线

并发题最容易陷入“API 背诵”，但真正应该先建立这条主线：

1. 是否存在共享可变状态
2. 如果有，谁能读，谁能写
3. 同步工具是什么
4. 是否能减少共享，而不是急着加锁
5. 结果是否能证明正确

### 错误回答示例

- “并发就是会几个 API”
- “有问题就加锁，先写出来再说”
- “只要程序能跑过几次就说明线程安全”


### English explanation

In an English interview, I would say:

- "Concurrency means knowing several APIs"
- "If you have any questions, lock them and write them down first before talking about them."
- "As long as the program can be run several times, it means it is thread safe"

### 面试官想听什么

- 你是否先从共享状态和正确性出发思考问题
- 你是否知道并发题的重点是证明同步关系，而不是罗列工具

### 项目里怎么说

我处理并发问题时会先确认共享状态和同步边界，再决定用锁、原子、队列还是减少共享，而不是先堆 API。

---

## 2. 线程 vs 进程

### 线程

- 同进程内共享地址空间
- 通信成本低
- 同步复杂


### English explanation

In an English interview, I would say:

- Shared address space within the same process
- Low communication cost
- Synchronization is complex

### 进程

- 资源隔离更强
- 故障隔离更强
- 通信和切换成本通常更高

### 面试要点

- 多线程的难点不在“开线程”，而在“共享状态”
- 多进程的难点不在“语法”，而在“通信和管理”

### 错误回答示例

- “线程就是轻量级进程，所以差不多”
- “多线程一定比多进程快”
- “进程线程区别只在创建方式”

### 面试官想听什么

- 你是否知道一个强调共享，一个强调隔离
- 你是否知道这会直接影响设计成本和故障隔离

### 项目里怎么说

如果更看重隔离和独立故障恢复，我会偏向多进程；如果更看重共享数据和低通信成本，我会偏向多线程，但同步设计会更谨慎。

---

## 3. `std::thread`

### 解决什么问题

直接创建线程执行一段并发任务。


### English explanation

In an English interview, I would say:

Directly create threads to perform a concurrent task.

### 最小示例

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

- `std::thread t(worker);` 创建线程并执行 `worker`
- `t.join();` 等待子线程结束
- 如果一个 `std::thread` 在 joinable 状态下析构，程序会出问题

### 什么时候直接用

- 线程数少
- 生命周期简单
- 不需要复杂任务调度

### 什么时候别急着用

- 高并发短任务
- 需要统一调度和复用线程

### 错误回答示例

- “`std::thread` 就是并发的最终方案”
- “创建线程后不需要管收尾”
- “线程越多越好”

### 面试官想听什么

- 你是否知道 `std::thread` 只是最底层直接线程抽象
- 你是否知道线程生命周期必须显式管理

### 项目里怎么说

线程数少、生命周期简单时我会直接用 `std::thread`；如果任务很多或需要统一调度，我会尽快上更高层抽象，比如线程池。

---

## 4. `join()` vs `detach()`

### `join()`

- 当前线程等待目标线程结束
- 生命周期更容易推导


### English explanation

In an English interview, I would say:

- The current thread waits for the target thread to end
- Life cycle is easier to derive

### `detach()`

- 线程脱离 `std::thread` 对象独立运行
- 更难管理资源和退出时机

### 面试建议

- 初学和业务代码里优先 `join`
- `detach` 要非常清楚资源生命周期才考虑

### 错误回答示例

- “`detach` 更高级”
- “不 `join` 也没关系”
- “后台线程都应该直接 `detach`”

### 面试官想听什么

- 你是否知道 `join` 更容易推导资源和退出顺序
- 你是否知道 `detach` 最大风险是生命周期失控

### 项目里怎么说

除非我能完全证明后台线程依赖的对象生命周期安全，否则我会优先 `join` 或使用托管式线程模型，而不是轻易 `detach`。

---

## 5. 竞态条件（race condition）

### 定义

多个线程并发访问共享数据，且至少一个线程写入，没有正确同步时，就可能出现竞态条件。


### English explanation

In an English interview, I would say:

When multiple threads access shared data concurrently, and at least one thread writes, without proper synchronization, a race condition may occur.

### 最小错误示例

```cpp
#include <iostream>
#include <thread>

int counter = 0;

void add() {
    for (int i = 0; i < 10000; ++i) {
        ++counter;
    }
}

int main() {
    std::thread t1(add);
    std::thread t2(add);
    t1.join();
    t2.join();
    std::cout << counter << '\n';
}
```

### 代码讲解

- `counter` 是共享可变状态
- `++counter` 不是原子复合操作
- 两个线程同时改它，结果依赖执行时序

### 真正重点

- 不是“线程多就错”
- 是“共享可变状态没有同步”

### 错误回答示例

- “偶发错误不算并发 bug”
- “只要本机没复现就没问题”
- “线程切换由系统决定，所以程序员没法管”

### 面试官想听什么

- 你是否知道竞态条件与时序有关，因此往往难复现
- 你是否能把问题根源归到共享可变状态和缺少同步

### 项目里怎么说

遇到这类问题我会优先减少共享状态，其次用明确同步边界保证正确，而不是依赖碰巧正确的执行时序。

---

## 6. `std::mutex`

### 解决什么问题

让同一时刻只有一个线程进入临界区，从而保护共享数据。


### English explanation

In an English interview, I would say:

Let only one thread enter the critical section at the same time to protect shared data.

### 示例

```cpp
#include <iostream>
#include <mutex>
#include <thread>

int counter = 0;
std::mutex mtx;

void add() {
    for (int i = 0; i < 10000; ++i) {
        std::lock_guard<std::mutex> lock(mtx);
        ++counter;
    }
}
```

### 代码讲解

- `mtx` 是共享锁对象
- `lock_guard` 在进入作用域时加锁
- `++counter` 是被保护的临界区操作

### 常见误区

- 锁不是越多越安全
- 锁范围过大反而会降低并发度

### 错误回答示例

- “加了锁就没有并发问题了”
- “锁只会影响性能，不影响设计”
- “每个变量一把锁就一定最好”

### 面试官想听什么

- 你是否知道锁保护的是共享数据和不变量
- 你是否知道锁的粒度也是设计的一部分

### 项目里怎么说

我会先用简单清晰的锁方案保证正确性，再根据瓶颈考虑细化锁粒度，而不是一开始就把同步设计得很复杂。

---

## 7. `std::lock_guard` vs `std::unique_lock`

### `lock_guard`

- 更轻量
- 适合简单作用域锁


### English explanation

In an English interview, I would say:

- More lightweight
- Suitable for simple scope locks

### `unique_lock`

- 更灵活
- 可延迟加锁、手动解锁、配合条件变量

### 示例

```cpp
#include <condition_variable>
#include <mutex>

std::mutex mtx;
std::condition_variable cv;
bool ready = false;

int main() {
    std::unique_lock<std::mutex> lock(mtx);
    cv.wait(lock, [] { return ready; });
}
```

### 代码讲解

- `unique_lock` 之所以常配合条件变量，是因为 `wait()` 需要临时释放和重新获取锁
- 这也是为什么这里不能直接用 `lock_guard`

### 错误回答示例

- “`unique_lock` 只是更慢的 `lock_guard`”
- “能用 `unique_lock` 就统一用它”
- “两者只差语法”

### 面试官想听什么

- 你是否知道一个更轻量，一个更灵活
- 你是否知道条件变量是二者的典型分界场景

### 项目里怎么说

简单作用域锁我优先 `lock_guard`；涉及等待、延迟加锁或更复杂控制时，我会换成 `unique_lock`。

---

## 8. 条件变量 `std::condition_variable`

### 解决什么问题

让线程“等待条件成立”，而不是忙等浪费 CPU。


### English explanation

In an English interview, I would say:

Let the thread "wait for the condition to be true" instead of wasting CPU by busy waiting.

### 核心模型

- 锁保护共享状态
- 条件变量等待/通知状态变化
- 等待时总要检查条件

### 典型骨架

```cpp
#include <condition_variable>
#include <mutex>

std::mutex mtx;
std::condition_variable cv;
bool ready = false;
```

### 面试重点

- 条件变量不是锁
- 它解决“等待条件”问题
- 要防伪唤醒，因此通常配合谓词或循环

### 错误回答示例

- “有锁就不需要条件变量”
- “`notify_one()` 一调用，对方就一定立刻执行”
- “条件变量就是高级互斥锁”

### 面试官想听什么

- 你是否知道条件变量和锁分工不同
- 你是否知道等待必须绑定条件检查

### 项目里怎么说

如果线程需要等待状态变化，而不是不停轮询，我会优先考虑条件变量，这样 CPU 开销和代码语义都更合理。

---

## 9. `std::atomic`

### 解决什么问题

为单个共享变量提供原子读写和某些原子复合操作。


### English explanation

In an English interview, I would say:

Provides atomic reads and writes and certain atomic composite operations for individual shared variables.

### 示例

```cpp
#include <atomic>

std::atomic<int> counter = 0;

int main() {
    ++counter;
}
```

### 代码讲解

- `std::atomic<int>` 表示该整数的操作具备原子性
- `++counter` 是线程安全的单变量自增

### 什么时候适合

- 计数器
- 标志位
- 简单状态发布

### 什么时候别乱用

- 多个变量必须保持一致
- 逻辑是“检查再修改”
- 需要复杂临界区

### 错误回答示例

- “原子变量能替代所有锁”
- “只要用了 `atomic` 就已经很高级”
- “原子天然适合复杂状态同步”

### 面试官想听什么

- 你是否知道原子只擅长简单共享状态
- 你是否知道复合逻辑仍可能需要锁

### 项目里怎么说

如果只是计数器、标志位这类简单状态，我会考虑 `atomic`；如果是多个字段要一起满足约束，我通常还是会用锁。

---

## 10. `atomic` 和 `mutex` 的边界

### 用 `atomic`

- 单个变量
- 简单状态
- 非常清晰的原子操作


### English explanation

In an English interview, I would say:

- single variable
- Simple state
- Very clear atomic operations

### 用 `mutex`

- 多个变量一起维护不变量
- 临界区里有复合逻辑
- 更看重可读性和可证明正确性

### 高频面试结论

- `atomic` 不是“更高级的锁”
- 锁也不是“落后方案”
- 正确性边界比局部性能更重要

### 错误回答示例

- “性能敏感就一定用原子”
- “锁都是给不会优化的人用的”
- “只要想快，就应该 lock-free”

### 面试官想听什么

- 你是否知道工具边界比工具热度更重要
- 你是否把正确性放在局部性能之前

### 项目里怎么说

我会先根据状态模型决定是否需要锁，再看是否值得把某个热点缩小成原子变量，而不是反过来为了追求“高级感”强行原子化。

---

## 11. `volatile` 为什么不等于线程安全

### 核心结论

`volatile` 只约束编译器优化，不提供线程同步语义，不保证原子性，也不保证跨线程可见性顺序。


### English explanation

In an English interview, I would say:

`volatile` only constrains compiler optimizations, does not provide thread synchronization semantics, does not guarantee atomicity, and does not guarantee cross-thread visibility ordering.

### 面试里最好直接说

- 线程同步用 `mutex` / `atomic`
- `volatile` 更多是低层硬件寄存器、特殊系统场景

### 错误回答示例

- “`volatile` 是轻量版线程同步”
- “多线程共享变量加 `volatile` 就够了”
- “它和原子变量差不多”

### 面试官想听什么

- 你是否明确知道 `volatile` 不提供同步语义
- 你是否能把它和并发工具区分开

### 项目里怎么说

业务并发代码里我不会把 `volatile` 当成同步方案；只有在非常明确的低层场景，我才会考虑它。

---

## 12. C++ 内存模型

### 解决什么问题

规定线程之间：

- 哪些写入对其他线程可见
- 什么叫同步
- 什么叫数据竞争
- 什么叫合法重排序


### English explanation

In an English interview, I would say:

Specify between threads:

- Which writes are visible to other threads
- What is synchronization?
- What is data competition?
- What is legal reordering?

### 真正难点

- 不是会不会写 `atomic`
- 而是会不会证明线程间可见性关系成立

### 错误回答示例

- “内存模型就是堆和栈”
- “只要用了原子变量，就不用关心顺序”
- “这只是编译器内部细节，业务代码不用理解”

### 面试官想听什么

- 你是否知道内存模型是在定义线程间可见性和同步关系
- 你是否知道数据竞争本身就是语言层未定义行为

### 项目里怎么说

即使业务代码不直接写复杂内存序，我也会理解内存模型的基础概念，因为这能帮助判断哪些并发写法是真的安全。

---

## 13. `memory_order`

### 四个高频层次

- `relaxed`：只保证原子性
- `release`：发布之前的写
- `acquire`：获取发布过来的写
- `seq_cst`：更强、更直观的一致顺序


### English explanation

In an English interview, I would say:

- `relaxed`: only guarantees atomicity
- `release`: written before release
- `acquire`: Get the published writing
- `seq_cst`: stronger, more intuitive consistent ordering

### 示例

```cpp
#include <atomic>

std::atomic<bool> ready = false;
int data = 0;

void producer() {
    data = 42;
    ready.store(true, std::memory_order_release);
}

void consumer() {
    if (ready.load(std::memory_order_acquire)) {
        // 此处可见 data = 42
    }
}
```

### 代码讲解

- `release` 把前面的写发布出去
- `acquire` 获取这次发布
- 这不是单看一行就能懂的机制，重点是“成对建立同步关系”

### 面试建议

- 业务代码里先优先锁
- 除非在写并发基础设施，否则别轻易炫弱内存序

### 错误回答示例

- “`relaxed` 最快，所以默认最好”
- “`seq_cst` 太慢，不能用”
- “只要会背几个名字就算懂了内存序”

### 面试官想听什么

- 你是否知道不同内存序是在控制可见性和重排序约束
- 你是否知道 release/acquire 通常要成对理解

### 项目里怎么说

除非我在写并发基础设施，否则我不会轻易下沉到复杂内存序调优；业务里优先简单可证明正确的同步方式。

---

## 14. 线程池

### 为什么存在

因为频繁创建和销毁线程成本高，线程池通过复用工作线程来处理大量短任务。


### English explanation

In an English interview, I would say:

Because frequent creation and destruction of threads is costly, the thread pool handles a large number of short tasks by reusing worker threads.

### 基础组成

- 工作线程集合
- 任务队列
- 互斥锁
- 条件变量
- 停止标志

### 基础示例

```cpp
#include <condition_variable>
#include <functional>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

class SimpleThreadPool {
public:
    explicit SimpleThreadPool(size_t n) : stop_(false) {
        for (size_t i = 0; i < n; ++i) {
            workers_.emplace_back([this] {
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(mtx_);
                        cv_.wait(lock, [this] {
                            return stop_ || !tasks_.empty();
                        });

                        if (stop_ && tasks_.empty()) {
                            return;
                        }

                        task = std::move(tasks_.front());
                        tasks_.pop();
                    }
                    task();
                }
            });
        }
    }

    ~SimpleThreadPool() {
        {
            std::lock_guard<std::mutex> lock(mtx_);
            stop_ = true;
        }
        cv_.notify_all();

        for (auto& worker : workers_) {
            worker.join();
        }
    }

    void submit(std::function<void()> task) {
        {
            std::lock_guard<std::mutex> lock(mtx_);
            tasks_.push(std::move(task));
        }
        cv_.notify_one();
    }

private:
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;
    std::mutex mtx_;
    std::condition_variable cv_;
    bool stop_;
};
```

### 代码讲解

- `workers_` 是工作线程集合
- `tasks_` 是待执行任务队列
- `std::function<void()>` 统一抽象任务类型
- `cv_.wait(...)` 让空闲线程阻塞等待任务
- `stop_` 配合析构和 `notify_all()` 控制优雅退出

### 面试官爱问什么

- 为什么不用每个任务都新建线程
- 如何优雅关闭线程池
- 如何支持返回值
- 如何限制任务队列长度

### 错误回答示例

- “线程池就是很多线程放在容器里”
- “只要是多线程程序都应该用线程池”
- “线程池的价值只有性能”

### 面试官想听什么

- 你是否知道线程池本质是“线程复用 + 任务调度”
- 你是否知道关闭协议、任务队列和同步机制同样重要

### 项目里怎么说

如果任务很多而且单个任务很短，我会考虑线程池来控制线程数量、复用工作线程、统一任务调度，而不是对每个任务都直接开线程。

---

## 15. `std::future` / `std::async`

### 解决什么问题

更高层地表达“异步执行任务，并在未来获取结果”。


### English explanation

In an English interview, I would say:

A higher-level expression of "execute a task asynchronously and get the result in the future".

### 示例

```cpp
#include <future>
#include <iostream>

int main() {
    auto fut = std::async(std::launch::async, [] {
        return 42;
    });

    std::cout << fut.get() << '\n';
}
```

### 代码讲解

- `std::async(...)` 启动异步任务
- `auto fut` 是 future，表示“未来结果”
- `fut.get()` 会等待任务完成并取回结果

### 和 `std::thread` 的区别

- `thread` 更偏“线程控制”
- `future` 更偏“结果交付”

### 错误回答示例

- “`async` 就是开线程的别名”
- “`future` 只是一个返回值盒子”
- “有线程池以后就完全不用理解它们”

### 面试官想听什么

- 你是否知道它们提供的是更高层异步结果模型
- 你是否知道它们和直接线程控制的关注点不同

### 项目里怎么说

如果只是简单地异步执行并在稍后取结果，我会优先考虑 `future/async` 这种更高层抽象；调度复杂时再考虑线程池或执行器。

---

## 16. 并发面试里的常见错误表达

- “多线程就是更快”
- “`volatile` 能保证线程安全”
- “用了 `atomic` 就不用考虑别的了”
- “线程池就是很多线程”
- “条件变量就是高级锁”
- “lock-free 一定比加锁高级”

---

## 17. 复习建议

- 先掌握共享状态、锁、条件变量、线程池主线
- 再学习 `atomic` 和内存序
- 任何并发题都先回答正确性，再回答性能
