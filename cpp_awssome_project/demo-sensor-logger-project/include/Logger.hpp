#pragma once

#include "ThreadSafeQueue.hpp"

#include <string>
#include <thread>

class Logger {
public:
    Logger() = default;
    ~Logger();

    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;

    void start();
    void log(std::string message);
    void stop();

private:
    void run();

    ThreadSafeQueue<std::string> queue_;
    std::thread worker_;
    bool started_ = false;
};
