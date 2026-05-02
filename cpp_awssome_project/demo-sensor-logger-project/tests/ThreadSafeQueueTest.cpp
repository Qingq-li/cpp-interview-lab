#include "ThreadSafeQueue.hpp"

#include <cassert>
#include <chrono>
#include <future>
#include <string>
#include <thread>

namespace {

void testFifoOrder() {
    ThreadSafeQueue<int> queue;

    queue.push(1);
    queue.push(2);
    queue.push(3);

    int value = 0;
    assert(queue.wait_and_pop(value));
    assert(value == 1);
    assert(queue.wait_and_pop(value));
    assert(value == 2);
    assert(queue.wait_and_pop(value));
    assert(value == 3);

    queue.shutdown();
}

void testMoveOnlyValue() {
    ThreadSafeQueue<std::string> queue;

    std::string message = "hello";
    queue.push(std::move(message));

    std::string output;
    assert(queue.wait_and_pop(output));
    assert(output == "hello");

    queue.shutdown();
}

void testShutdownWakesConsumer() {
    ThreadSafeQueue<int> queue;

    auto result = std::async(std::launch::async, [&queue] {
        int value = 0;
        return queue.wait_and_pop(value);
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    queue.shutdown();

    assert(result.get() == false);
}

} // namespace

int main() {
    testFifoOrder();
    testMoveOnlyValue();
    testShutdownWakesConsumer();

    return 0;
}
