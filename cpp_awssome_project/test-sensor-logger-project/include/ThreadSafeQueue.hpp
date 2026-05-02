#pragma once

#include <condition_variable> // std::condition_variable, std::condition_variable::wait, std::condition_variable::notify_one
#include <mutex> // std::mutex, std::lock_guard, std::unique_lock
#include <queue>
#include <utility>


template <typename T>
class ThreadSafeQueue {
    public:

        ThreadSafeQueue() = default;
        ThreadSafeQueue(const ThreadSafeQueue&) = delete;
        ThreadSafeQueue& operator=(const ThreadSafeQueue&) = delete;

        void push(T value){
            {
                std::lock_guard<std::mutex> lock(mutex_);
                queue_.push(std::move(value));
            }
            condition_variable_.notify_one();
        }

        bool wait_and_pop(T& value){
            std::unique_lock<std::mutex> lock(mutex_);
            condition_variable_.wait(lock, [this] {
                return shutdown_ || !queue_.empty();
            });

            if (queue_.empty()) {
                return false;
            }

            value = std::move(queue_.front());
            queue_.pop();
            return true;
        }

        bool empty() const{
            std::lock_guard<std::mutex> lock1(mutex_);
            return queue_.empty();
        }

        void shutdown(){
            {
                std::lock_guard<std::mutex> lock(mutex_);
                shutdown_ = true;
            }
            condition_variable_.notify_all();
        }

    private:
        std::queue<T> queue_;
        mutable std::mutex mutex_;
        std::condition_variable condition_variable_;
        bool shutdown_ = false;
};
