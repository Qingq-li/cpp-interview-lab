#include "ThreadPool.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <memory>
#include <numeric>
#include <vector>

struct WorkItem {
    int id = 0;
    std::vector<std::uint64_t> payload;
};

int main()
{
    constexpr int worker_count = 4;
    constexpr int task_count = 10000;
    constexpr int payload_size = 64;

    ThreadPool pool(worker_count);

    std::atomic<int> finished_count{0};
    std::atomic<std::uint64_t> total_checksum{0};

    const auto start = std::chrono::steady_clock::now();

    for (int task_id = 0; task_id < task_count; ++task_id) {
        pool.submit([task_id, &finished_count, &total_checksum] {
            auto item = std::make_unique<WorkItem>();
            item->id = task_id;
            item->payload.reserve(payload_size);

            for (int i = 0; i < payload_size; ++i) {
                item->payload.push_back(
                    static_cast<std::uint64_t>(task_id) * 100ULL
                    + static_cast<std::uint64_t>(i));
            }

            const auto sum = std::accumulate(
                item->payload.begin(),
                item->payload.end(),
                std::uint64_t{0});

            total_checksum.fetch_add(sum, std::memory_order_relaxed);
            finished_count.fetch_add(1, std::memory_order_relaxed);
        });
    }

    pool.shutdown();

    const auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start);

    std::cout << "tasks = " << task_count << '\n';
    std::cout << "finished = " << finished_count.load() << '\n';
    std::cout << "total checksum = " << total_checksum.load() << '\n';
    std::cout << "elapsed = " << elapsed_ms.count() << " ms\n";

    return finished_count.load() == task_count ? 0 : 1;
}
