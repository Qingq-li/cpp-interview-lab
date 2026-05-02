#include "Logger.hpp"

#include <iostream>
#include <utility>

Logger::~Logger() {
    stop();
}

void Logger::start() {
    if (started_) {
        return;
    }

    started_ = true;
    worker_ = std::thread(&Logger::run, this);
}

void Logger::log(std::string message) {
    queue_.push(std::move(message));
}

void Logger::stop() {
    if (!started_) {
        return;
    }

    queue_.shutdown();

    if (worker_.joinable()) {
        worker_.join();
    }

    started_ = false;
}

void Logger::run() {
    std::string message;

    while (queue_.wait_and_pop(message)) {
        std::cout << message << '\n';
    }
}
