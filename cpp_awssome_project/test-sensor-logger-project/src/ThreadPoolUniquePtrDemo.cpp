#include <atomic> // std::atomic
#include <chrono> // std::chrono::steady_clock, std::chrono::duration_cast
#include <condition_variable> // std::condition_variable
#include <cstdint> // std::uint64_t
#include <exception> // std::exception
#include <future> // std::future, std::packaged_task
#include <iostream> // std::cout
#include <memory> // std::unique_ptr, std::make_unique
#include <mutex> // std::mutex, std::lock_guard, std::unique_lock
#include <numeric> // std::accumulate
#include <queue> // std::queue
#include <stdexcept> // std::runtime_error
#include <thread> // std::thread
#include <type_traits> // std::invoke_result_t
#include <utility> // std::move, std::forward
#include <vector> // std::vector

// 这个示例演示一个更工程化的版本：
// 1. producer 线程只负责创建 WorkItem。
// 2. ThreadPool 维护固定数量 worker 线程。
// 3. producer 把“处理 WorkItem 的任务”提交给 ThreadPool。
// 4. WorkItem 仍然用 std::unique_ptr 表达独占所有权。
//
// 三个文件的核心区别：
//
// ThreadSafeQueue.cpp:
//     只演示 ThreadSafeQueue<int> 的基本 push / wait_and_pop。
//     它更像“队列 API 怎么用”的最小例子，没有 producer 线程，也没有线程池。
//
// MultiThreadUniquePtrDemo.cpp:
//     队列里放的是数据：
//         ThreadSafeQueue<std::unique_ptr<WorkItem>>
//     producer 把 WorkItem push 到队列。
//     consumer 线程手动 while (queue.wait_and_pop(item)) 取数据并处理。
//     重点是 producer-consumer、shutdown、join、unique_ptr 所有权转移。
//
// ThreadPoolUniquePtrDemo.cpp:
//     线程池队列里放的是任务：
//         std::queue<MoveOnlyTask>
//     producer 不直接指定哪个 consumer 处理数据，只 submit 一个 callable。
//     worker 线程由 ThreadPool 统一管理，自动取任务执行。
//     重点是固定 worker、任务提交、任务队列、wait_idle、shutdown。
//
// 最短心智模型：
//     MultiThreadUniquePtrDemo:
//         “把数据放进队列，让 consumer 取数据”
//
//     ThreadPoolUniquePtrDemo:
//         “把要执行的工作放进队列，让 worker 执行工作”
//
// 重要点：
// C++17 的 std::function 要求目标 callable 可拷贝。
// 但是捕获 std::unique_ptr 的 lambda 是 move-only，不可拷贝：
//
//     auto item = std::make_unique<WorkItem>();
//     [item = std::move(item)] { ... }  // 这个 lambda 不能复制
//
// 所以下面的线程池没有用 std::function<void()> 存任务，而是实现了一个
// MoveOnlyTask，用来保存 move-only callable。

struct WorkItem {
    int producer_id = 0;
    int sequence = 0;
    std::vector<std::uint64_t> payload;
};

// MoveOnlyTask 是这个 demo 的关键教学点之一。
//
// 很多线程池教程会写：
//
//     std::queue<std::function<void()>> tasks;
//
// 但 std::function 在 C++17 里要求里面保存的 callable 可以复制。
// 捕获 unique_ptr 的 lambda 不可复制，只能移动，所以 std::function<void()> 装不下。
//
// MoveOnlyTask 的作用：
//     只要求任务可以移动，不要求任务可以复制。
//     这样任务 lambda 就可以安全捕获 unique_ptr。
class MoveOnlyTask {
public:
    MoveOnlyTask() = default;

    template <typename F>
    explicit MoveOnlyTask(F&& function)
        : callable_(std::make_unique<Model<F>>(std::forward<F>(function)))
    {
    }

    MoveOnlyTask(MoveOnlyTask&&) noexcept = default;
    MoveOnlyTask& operator=(MoveOnlyTask&&) noexcept = default;

    MoveOnlyTask(const MoveOnlyTask&) = delete;
    MoveOnlyTask& operator=(const MoveOnlyTask&) = delete;

    void operator()()
    {
        callable_->call();
    }

private:
    struct Concept {
        virtual ~Concept() = default;
        virtual void call() = 0;
    };

    template <typename F>
    struct Model final : Concept {
        explicit Model(F&& function)
            : function_(std::forward<F>(function))
        {
        }

        void call() override
        {
            function_();
        }

        F function_;
    };

    std::unique_ptr<Concept> callable_;
};

class ThreadPool {
public:
    explicit ThreadPool(std::size_t worker_count)
    {
        workers_.reserve(worker_count);

        for (std::size_t id = 0; id < worker_count; ++id) {
            // 线程池的 worker 是长期存在的线程。
            // 它们不是“每来一个 WorkItem 创建一个线程”，而是反复执行 worker_loop。
            workers_.emplace_back([this] {
                worker_loop();
            });
        }
    }

    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    ~ThreadPool()
    {
        shutdown();
    }

    template <typename F>
    auto submit(F&& function) -> std::future<std::invoke_result_t<F&>>
    {
        using Result = std::invoke_result_t<F&>;

        // submit 是线程池和普通 producer-consumer 的最大区别。
        //
        // MultiThreadUniquePtrDemo.cpp:
        //     producer 调用 queue.push(std::move(item));
        //     队列保存的是 WorkItem 数据。
        //
        // 这里：
        //     producer 调用 pool.submit(lambda);
        //     队列保存的是“稍后要执行的 lambda 任务”。
        // packaged_task 把一个 callable 包起来，并提供 future。
        // 即使调用者不保存这个 future，任务本身仍然会在 worker 线程执行。
        std::packaged_task<Result()> task(std::forward<F>(function));
        auto result = task.get_future();

        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (stopping_) {
                throw std::runtime_error("submit on stopped ThreadPool");
            }

            // task 是 move-only；这里再用 move-only lambda 包一层。
            // 这也是为什么任务队列类型不能是 std::function<void()>。
            tasks_.emplace([task = std::move(task)]() mutable {
                task();
            });
        }

        cv_.notify_one();
        return result;
    }

    void wait_idle()
    {
        // wait_idle 等待“当前已经提交的任务全部做完”。
        //
        // 只检查 tasks_.empty() 不够：
        //     队列可能已经空了，但某个 worker 正在执行刚取出的任务。
        //
        // 所以还要检查 active_tasks_ == 0。
        std::unique_lock<std::mutex> lock(mutex_);
        idle_cv_.wait(lock, [this] {
            return tasks_.empty() && active_tasks_ == 0;
        });
    }

    void shutdown()
    {
        // shutdown 表示：
        //     不再接受新任务。
        //     唤醒所有正在 cv_.wait 的 worker。
        //     worker 会把队列里已有任务执行完，然后退出。
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (stopping_) {
                return;
            }
            stopping_ = true;
        }

        cv_.notify_all();

        for (auto& worker : workers_) {
            if (worker.joinable()) {
                worker.join();
            }
        }
    }

private:
    void worker_loop()
    {
        for (;;) {
            MoveOnlyTask task;

            {
                std::unique_lock<std::mutex> lock(mutex_);

                // worker 空闲时睡在 condition_variable 上，不会忙等消耗 CPU。
                //
                // 这和 MultiThreadUniquePtrDemo.cpp 里的 wait_and_pop 思想一样：
                //     没任务 -> 阻塞睡眠
                //     有任务 -> 被 notify_one 唤醒
                //     shutdown -> 被 notify_all 唤醒并退出
                cv_.wait(lock, [this] {
                    return stopping_ || !tasks_.empty();
                });

                // stopping_ 为 true 但队列还有任务时，不能马上退出；
                // 否则已经 submit 的任务会丢失。
                //
                // 只有 “stopping_ && tasks_.empty()” 同时成立，worker 才退出。
                if (stopping_ && tasks_.empty()) {
                    return;
                }

                // 把任务从共享队列移动到局部变量 task。
                // 出锁之后再执行 task()，避免长时间占用 mutex_。
                task = std::move(tasks_.front());
                tasks_.pop();
                ++active_tasks_;
            }

            // 真正的业务逻辑在这里运行。
            // 本 demo 中，task() 会计算 WorkItem payload 的 checksum。
            task();

            {
                std::lock_guard<std::mutex> lock(mutex_);
                --active_tasks_;

                // 如果队列空了，而且没有 worker 正在执行任务，
                // wait_idle() 就可以返回。
                if (tasks_.empty() && active_tasks_ == 0) {
                    idle_cv_.notify_all();
                }
            }
        }
    }

    std::vector<std::thread> workers_; // 固定数量 worker 线程，构造 ThreadPool 时创建。
    std::queue<MoveOnlyTask> tasks_; // 等待执行的任务队列，不直接保存 WorkItem 数据。
    std::mutex mutex_; // 保护 tasks_、stopping_、active_tasks_。
    std::condition_variable cv_; // worker 等新任务或 shutdown。
    std::condition_variable idle_cv_; // main 等线程池变为空闲。
    bool stopping_ = false; // true 表示不再接受新任务，并要求 worker 处理完剩余任务后退出。
    std::size_t active_tasks_ = 0; // 已经被 worker 取走、正在执行但还没完成的任务数。
};

int main()
{
    constexpr int producer_count = 4;
    constexpr int worker_count = 4;
    constexpr int items_per_producer = 50000;
    constexpr int payload_size = 64;
    constexpr int expected_task_count = producer_count * items_per_producer;

    // ThreadPool 构造时立即创建 worker_count 个 worker 线程。
    // 之后 submit 只是把任务放进队列，不会每次 submit 都创建新线程。
    ThreadPool pool(worker_count);

    // produced_count:
    //     producer 成功 submit 的任务数量。
    //
    // consumed_count:
    //     worker 实际执行完成的任务数量。
    //
    // total_checksum:
    //     所有 WorkItem payload 的总校验和。
    //
    // 这些变量会被多个 producer / worker 线程同时更新，所以使用 atomic。
    std::atomic<int> produced_count{0};
    std::atomic<int> consumed_count{0};
    std::atomic<std::uint64_t> total_checksum{0};

    // cout 本身可以被多个线程同时调用，但输出内容可能交错。
    // 这里用 mutex 只保护演示日志，让每行输出更容易阅读。
    std::mutex cout_mutex;

    // 注意：这里仍然有 producer 线程。
    // 线程池替代的是 consumer 线程，不是 producer。
    //
    // MultiThreadUniquePtrDemo.cpp:
    //     producers + consumers 都由 main 手动创建和 join。
    //
    // 本文件：
    //     producers 仍由 main 创建。
    //     worker 线程由 ThreadPool 内部创建和 join。
    std::vector<std::thread> producers;

    const auto start = std::chrono::steady_clock::now();

    for (int producer_id = 0; producer_id < producer_count; ++producer_id) {
        producers.emplace_back([producer_id, &pool, &produced_count, &consumed_count,
                                &total_checksum, &cout_mutex] {
            for (int seq = 0; seq < items_per_producer; ++seq) {
                auto item = std::make_unique<WorkItem>();
                item->producer_id = producer_id;
                item->sequence = seq;
                item->payload.reserve(payload_size);

                for (int i = 0; i < payload_size; ++i) {
                    item->payload.push_back(
                        static_cast<std::uint64_t>(producer_id + 1) * 1000000ULL
                        + static_cast<std::uint64_t>(seq) * 100ULL
                        + static_cast<std::uint64_t>(i));
                }

                // 线程池版本的核心点：
                // item 是 unique_ptr，不能复制进任务。
                // 这里用 C++14 初始化捕获，把 item 的所有权移动进 lambda。
                // submit 后，producer 里的 item 变成 nullptr；真正的 WorkItem
                // 将由某个 worker 线程处理并自动释放。
                //
                // 对比 MultiThreadUniquePtrDemo.cpp：
                //     queue.push(std::move(item));
                //
                // 这里不是把 WorkItem 数据放进外部 queue；
                // 而是把“处理这个 WorkItem 的 lambda”放进 ThreadPool 的任务队列。
                pool.submit([item = std::move(item), &consumed_count, &total_checksum] {
                    const auto sum = std::accumulate(
                        item->payload.begin(),
                        item->payload.end(),
                        std::uint64_t{0});

                    total_checksum.fetch_add(sum, std::memory_order_relaxed);
                    consumed_count.fetch_add(1, std::memory_order_relaxed);
                });

                produced_count.fetch_add(1, std::memory_order_relaxed);

                if (seq % 25000 == 0) {
                    std::lock_guard<std::mutex> lock(cout_mutex);
                    std::cout << "[producer " << producer_id << "] submitted "
                              << seq << " tasks\n";
                }
            }
        });
    }

    for (auto& producer : producers) {
        producer.join();
    }

    {
        std::lock_guard<std::mutex> lock(cout_mutex);
        std::cout << "All producers joined. Waiting for thread pool to become idle...\n";
    }

    // 等待所有已经提交的任务执行完成。
    // 注意：这不是停止线程池，只是等待任务队列清空且没有 worker 正在执行任务。
    pool.wait_idle();

    // shutdown 会通知 worker 退出，并 join 所有 worker。
    // 即使不手动调用，ThreadPool 析构函数也会调用；这里显式调用是为了演示生命周期。
    pool.shutdown();

    const auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start);

    std::cout << "produced = " << produced_count.load()
              << ", consumed = " << consumed_count.load() << '\n';
    std::cout << "expected tasks = " << expected_task_count << '\n';
    std::cout << "total checksum = " << total_checksum.load() << '\n';
    std::cout << "elapsed = " << elapsed_ms.count() << " ms\n";

    return produced_count.load() == expected_task_count
        && consumed_count.load() == expected_task_count
        ? 0
        : 1;
}
