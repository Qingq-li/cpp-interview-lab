#include <iostream>
#include <vector>
#include <queue>
#include <memory>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <chrono>
#include <numeric>

// ================= Timer =================

class Timer {
public:
    Timer() : start_(std::chrono::steady_clock::now()) {}

    long long elapsed_us() const {
        auto end = std::chrono::steady_clock::now();
        return std::chrono::duration_cast<std::chrono::microseconds>(
            end - start_
        ).count();
    }

private:
    std::chrono::steady_clock::time_point start_;
};

// ================= Thread-safe Queue =================

template <typename T>
class ThreadSafeQueue {
public:
    ThreadSafeQueue() = default;
    ThreadSafeQueue(const ThreadSafeQueue&) = delete;
    ThreadSafeQueue& operator=(const ThreadSafeQueue&) = delete;

    void push(T value) {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            queue_.push(std::move(value));
        }
        cv_.notify_one();
    }

    void wait_and_pop(T& value) {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this] {
            return !queue_.empty();
        });

        value = std::move(queue_.front());
        queue_.pop();
    }

private:
    std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<T> queue_;
};

// ================= Polymorphic Task Base =================

class Task {
public:
    explicit Task(int id) : id_(id) {}

    virtual ~Task() = default;

    int id() const {
        return id_;
    }

    virtual long long process() = 0;

private:
    int id_;
};

// ================= Derived Task 1 =================

class SumTask : public Task {
public:
    SumTask(int id, std::vector<int> data)
        : Task(id), data_(std::move(data)) {}

    long long process() override {
        long long sum = 0;
        for (int v : data_) {
            sum += v;
        }
        return sum;
    }

private:
    std::vector<int> data_;
};

// ================= Derived Task 2 =================

class MultiplyTask : public Task {
public:
    MultiplyTask(int id, int a, int b)
        : Task(id), a_(a), b_(b) {}

    long long process() override {
        return static_cast<long long>(a_) * b_;
    }

private:
    int a_;
    int b_;
};

// ================= Thread Pool =================

class ThreadPool {
public:
    explicit ThreadPool(int worker_count)
        : partial_sums_(worker_count, 0) {

        workers_.reserve(worker_count);

        for (int i = 0; i < worker_count; ++i) {
            workers_.emplace_back([this, i] {
                worker_loop(i);
            });
        }
    }

    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    ~ThreadPool() {
        stop();
    }

    void submit(std::unique_ptr<Task> task) {
        queue_.push(std::move(task));
    }

    void stop() {
        if (stopped_) {
            return;
        }

        stopped_ = true;

        for (size_t i = 0; i < workers_.size(); ++i) {
            queue_.push(nullptr);
        }

        for (auto& worker : workers_) {
            if (worker.joinable()) {
                worker.join();
            }
        }
    }

    long long total_sum() const {
        long long total = 0;
        for (auto v : partial_sums_) {
            total += v;
        }
        return total;
    }

private:
    void worker_loop(int worker_id) {
        long long local_thread_sum = 0;

        while (true) {
            std::unique_ptr<Task> task;
            queue_.wait_and_pop(task);

            if (!task) {
                break;
            }

            long long result = task->process();
            local_thread_sum += result;

            // 性能测试时不要频繁打印
            if (task->id() % 10000 == 0) {
                std::cout << "Worker " << worker_id
                          << " processed task " << task->id()
                          << ", result = " << result << '\n';
            }
        }

        partial_sums_[worker_id] = local_thread_sum;
    }

private:
    ThreadSafeQueue<std::unique_ptr<Task>> queue_;
    std::vector<std::thread> workers_;
    std::vector<long long> partial_sums_;
    bool stopped_ = false;
};

// ================= Main =================

int main() {
    constexpr int WORKER_COUNT = 4;
    constexpr int TASK_COUNT = 100000;

    Timer timer;

    ThreadPool pool(WORKER_COUNT);

    for (int i = 0; i < TASK_COUNT; ++i) {
        if (i % 2 == 0) {
            std::vector<int> data;
            data.reserve(100);

            for (int j = 0; j < 100; ++j) {
                data.push_back(j);
            }

            pool.submit(std::make_unique<SumTask>(i, std::move(data)));
        } else {
            pool.submit(std::make_unique<MultiplyTask>(i, i, 2));
        }
    }

    pool.stop();

    std::cout << "\nFINAL SUM: " << pool.total_sum() << '\n';
    std::cout << "TIME COST: " << timer.elapsed_us() << " us\n";

    return 0;
}