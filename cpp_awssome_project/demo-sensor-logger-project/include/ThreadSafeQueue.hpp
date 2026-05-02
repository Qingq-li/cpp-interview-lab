#pragma once

#include <condition_variable>
#include <mutex>
#include <queue>

// A small blocking queue for the producer-consumer pattern.
//
// Producers call push(). Consumers call wait_and_pop(), which sleeps while the
// queue is empty and wakes up when data arrives or shutdown() is called.
template <typename T>
class ThreadSafeQueue {
public:
    ThreadSafeQueue() = default; // default constructor

    ThreadSafeQueue(const ThreadSafeQueue&) = delete; // no copying
    ThreadSafeQueue& operator=(const ThreadSafeQueue&) = delete; // no assignment

    void push(T item) {
        {
            // Keep the lock scope short: only protect shared queue state.
            std::lock_guard<std::mutex> lock(mutex_);
            if (shutdown_) {
                return;
            }
            queue_.push(std::move(item)); // Use move semantics if possible.
        }

        // Notify after releasing the lock so the waiting thread can run.
        cv_.notify_one();
    }

    bool wait_and_pop(T& item) {
        std::unique_lock<std::mutex> lock(mutex_);

        // The predicate handles spurious wakeups and keeps waiting until there
        // is real work or the queue is shutting down.
        cv_.wait(lock, [this] {
            return shutdown_ || !queue_.empty();
        });

        if (queue_.empty()) {
            return false;
        }

        item = std::move(queue_.front());
        queue_.pop();
        return true;
    }

    void shutdown() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            shutdown_ = true;
        }

        // Wake all consumers so nobody stays blocked during program exit.
        cv_.notify_all();
    }

    bool empty() const {
        // std::lock_guard<std::mutex> lock(mutex_);
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this]{return !queue_.empty();});
        return queue_.empty();
        
    }

private:
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<T> queue_;
    bool shutdown_ = false;
};
