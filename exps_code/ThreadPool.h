#pragma once

#include "ThreadSafeQueue.h"

#include <atomic>
#include <condition_variable>
#include <cstddef>
#include <functional>
#include <mutex>
#include <thread>
#include <utility>
#include <vector>

// 一个教学型的小线程池：
// 1. 固定数量的 worker 线程常驻等待任务
// 2. 外部通过 submit() 投递任务
// 3. worker 从队列里取出任务并执行
//
// 这里故意不做 future、优先级调度等高级功能，
// 目标是把“线程池最核心的结构”讲清楚。
class ThreadPool {
public:
    explicit ThreadPool(std::size_t workerCount) {
        workers_.reserve(workerCount);

        for (std::size_t i = 0; i < workerCount; ++i) {
            // 这里的 [this, i] { ... } 就是 lambda 表达式。
            // [this, i] 是捕获列表：
            // - this: 让 lambda 可以访问当前对象的成员
            // - i: 把当前 worker 的编号拷贝进 lambda
            workers_.emplace_back([this, i] {
                workerLoop(i);
            });
        }
    }

    ~ThreadPool() {
        shutdown();
    }

    void submit(std::function<void()> task) {
        {
            std::lock_guard<std::mutex> lock(stateMutex_);
            if (stopped_) {
                return;
            }
            ++pendingTasks_;
        }

        // 这里把“待执行逻辑”包装成 std::function<void()>，
        // 线程池就不需要关心任务具体来自哪里，只负责统一执行。
        tasks_.push(std::move(task));
    }

    void waitUntilEmpty() {
        std::unique_lock<std::mutex> lock(stateMutex_);
        finishedCv_.wait(lock, [this] {
            return pendingTasks_ == 0;
        });
    }

    void shutdown() {
        {
            std::lock_guard<std::mutex> lock(stateMutex_);
            if (stopped_) {
                return;
            }
            stopped_ = true;
        }

        tasks_.close();

        for (auto& worker : workers_) {
            if (worker.joinable()) {
                worker.join();
            }
        }
    }

private:
    void workerLoop(std::size_t workerIndex) {
        while (true) {
            auto task = tasks_.waitAndPop();
            if (!task.has_value()) {
                break;
            }

            (*task)();

            {
                std::lock_guard<std::mutex> lock(stateMutex_);
                --pendingTasks_;
                if (pendingTasks_ == 0) {
                    finishedCv_.notify_all();
                }
            }
        }
    }

    ThreadSafeQueue<std::function<void()>> tasks_;
    std::vector<std::thread> workers_;

    // 这两个成员用于“等待线程池把所有任务做完”。
    std::mutex stateMutex_;
    std::condition_variable finishedCv_;
    std::size_t pendingTasks_ = 0;
    bool stopped_ = false;
};
