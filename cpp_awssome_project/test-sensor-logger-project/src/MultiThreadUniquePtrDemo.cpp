#include "ThreadSafeQueue.hpp"

#include <atomic> // std::atomic, std::memory_order_relaxed
#include <chrono> // std::chrono::steady_clock, std::chrono::duration_cast, std::chrono::milliseconds
#include <cstdint> // std::uint64_t
#include <numeric> // std::accumulate
#include <iostream> // std::cout, std::endl
#include <memory> // std::unique_ptr, std::make_unique
#include <thread> // std::thread
#include <vector> // std::vector

// 这个示例演示：
// 1. 多个 producer 线程生成 WorkItem。
// 2. WorkItem 用 std::unique_ptr 管理，放入线程安全队列时通过 std::move 转移所有权。
// 3. 多个 consumer 线程从队列取出任务并计算 checksum。
//
// 标准版本提示：
// - C++11: std::thread, std::atomic, std::unique_ptr, lambda, constexpr,
//          std::chrono, 统一初始化 std::uint64_t{0}。
// - C++14: std::make_unique。
// - C++17: 本项目 CMake 使用 C++17 编译；本文件没有依赖 C++17 专属语法。
// - C++20: 本文件没有依赖 C++20 专属语法；如果使用 std::jthread 才是 C++20。
struct WorkItem {
    // 成员默认初始化是 C++11 特性。
    // 好处：即使 WorkItem 被默认构造，基础字段也有确定初值。
    int producer_id = 0;
    int sequence = 0;

    // payload 模拟一段较大的任务数据。vector 的内存由对象自己管理；
    // WorkItem 被 unique_ptr 拥有时，payload 会跟随 WorkItem 一起释放。
    std::vector<std::uint64_t> payload;
};

struct ConsumerStats {
    // 每个 consumer 只更新 stats[id]，没有多个线程同时写同一个 ConsumerStats。
    // 因此这里不需要 atomic；最终在所有 consumer join() 后统一读取。
    std::uint64_t items = 0;
    std::uint64_t checksum = 0;
};

int main() {
    // constexpr 是 C++11 特性，表示这个值可以在编译期求值。
    // 这里用 constexpr 的原因：
    // - 这些配置在运行期间不会改变，语义上比普通 int 更明确。
    // - 编译器可以把它们当常量优化。
    // - 如果未来用于数组大小、模板参数等需要编译期常量的地方，也能直接使用。
    constexpr int producer_count = 8;      // producer 线程数量
    constexpr int consumer_count = 8;      // consumer 线程数量
    constexpr int items_per_producer = 2500000; // 每个 producer 生成的任务数
    constexpr int payload_size = 64;       // 每个任务 payload 中的整数数量

    // 队列元素类型是 std::unique_ptr<WorkItem>。
    // unique_ptr 是 C++11 的独占所有权智能指针：同一时刻只有一个 owner。
    // 任务进入队列后，producer 不再拥有它；consumer 取出后成为新的 owner。
    // 这避免了手动 delete，也避免了多个线程共享裸指针导致生命周期不清晰。
    ThreadSafeQueue<std::unique_ptr<WorkItem>> queue;

    // atomic 是 C++11 特性，用于多个线程安全地读写同一个计数器。
    // produced_count / consumed_count 会被多个线程同时更新，所以必须避免数据竞争。
    std::atomic<int> produced_count{0};
    std::atomic<int> consumed_count{0};

    // std::thread 是 C++11 特性。
    // producers / consumers 保存线程对象，main 线程稍后必须 join() 等待它们结束。
    std::vector<std::thread> producers;
    std::vector<std::thread> consumers;

    // stats 的大小固定为 consumer_count。
    // 每个 consumer 线程只写自己的 stats[id]，所以不会互相覆盖。
    std::vector<ConsumerStats> stats(consumer_count);

    // steady_clock 是 C++11 特性，适合测量耗时。
    // 它是单调时钟，不受系统时间被手动调整的影响。
    const auto start = std::chrono::steady_clock::now();

    for (int id = 0; id < consumer_count; ++id) {
        // emplace_back 直接在 vector 末尾构造一个 std::thread。
        // 对比 push_back(std::thread(...))，emplace_back 可以少写临时对象形式，
        // 表达的是“把这个线程就地放进容器”。emplace_back 是 C++11 特性。
        consumers.emplace_back([id, &queue, &stats, &consumed_count] {
            // lambda 是 C++11 特性。
            // 捕获说明：
            // - id 按值捕获：每个线程保存自己的 consumer id。
            //   如果用 &id 引用捕获，循环继续改变 id 后，线程可能读到错误的值。
            // - queue/stats/consumed_count 按引用捕获：线程要操作 main 中同一份对象。
            std::unique_ptr<WorkItem> item;

            // wait_and_pop 会阻塞等待任务。
            // 返回 false 表示队列 shutdown 且没有剩余任务，consumer 可以退出循环。
            while (queue.wait_and_pop(item)) {
                // std::accumulate 来自 <numeric>，用于把一个范围内的值累加成一个结果。
                // 第 1、2 个参数是 begin/end 迭代器，表示要累加 item->payload 的全部元素。
                // 第 3 个参数 std::uint64_t{0} 是初始值，同时决定累加结果的类型。
                //
                // 为什么不用 0？
                // - 0 的类型是 int，accumulate 的内部累加变量会以 int 开始，
                //   大数据时可能先发生 int 溢出或类型不符合预期。
                // - std::uint64_t{0} 明确要求用 64 位无符号整数累加。
                //
                // std::accumulate 很早就存在；这里的统一初始化 T{0} 是 C++11 风格。
                const auto sum = std::accumulate(
                    item->payload.begin(),
                    item->payload.end(),
                    std::uint64_t{0});

                // 这里不需要锁：
                // stats[id] 只属于当前 consumer 线程。
                stats[id].items += 1;
                stats[id].checksum += sum;

                // memory_order_relaxed 表示这里只需要原子地递增计数，
                // 不要求它和其他内存读写建立先后可见性关系。
                // 因为最终正确性由 join() 和队列同步保证，计数器只是统计用途。
                consumed_count.fetch_add(1, std::memory_order_relaxed);

                if (stats[id].items % 20000 == 0) {
                    std::cout << "[consumer " << id << "] processed "
                              << stats[id].items << " items\n";
                }
            }
        });
    }
    std::cout << std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start).count() << "All consumers" << consumers.size() << " started.\n";

    for (int id = 0; id < producer_count; ++id) {
        // 每次 emplace_back 创建一个 producer 线程。
        // items_per_producer / payload_size 是 constexpr，lambda 可以直接读取这些常量。
        producers.emplace_back([id, &queue, &produced_count] {
            for (int seq = 0; seq < items_per_producer; ++seq) {
                // std::make_unique 是 C++14 特性。
                // 推荐用 make_unique 而不是 new WorkItem：
                // - 代码更短。
                // - 异常安全，不会在复杂表达式中泄漏裸指针。
                // - 明确返回 std::unique_ptr<WorkItem>，表达独占所有权。
                auto item = std::make_unique<WorkItem>();
                item->producer_id = id;
                item->sequence = seq;

                // reserve 只预留容量，不改变 vector 的 size。
                // 已知后面会 push payload_size 次，提前 reserve 可以减少反复扩容和拷贝/移动。
                item->payload.reserve(payload_size);

                for (int i = 0; i < payload_size; ++i) {
                    // push_back 在 vector 末尾追加一个元素。
                    // static_cast<std::uint64_t> 明确把参与计算的值转为 64 位无符号整数，
                    // 避免 int 参与大数计算时产生不必要的窄类型风险。
                    item->payload.push_back(
                        static_cast<std::uint64_t>(id + 1) * 1000000ULL
                        + static_cast<std::uint64_t>(seq) * 100ULL
                        + static_cast<std::uint64_t>(i));
                }

                // unique_ptr 不能复制，只能移动。
                // std::move 不会移动数据本身；它只是把 item 转成右值，
                // 允许 queue.push 接管 WorkItem 的所有权。
                // push 之后，当前 item 变为空指针，producer 不应再解引用它。
                queue.push(std::move(item));

                // relaxed 足够，因为这里只统计生成数量，不用它同步 WorkItem 内容。
                produced_count.fetch_add(1, std::memory_order_relaxed);

                if (seq % 10000 == 0) {
                    std::cout << "[producer " << id << "] generated "
                              << seq << " items\n";
                }
            }
        });
    }
    std::cout << std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start).count() << "All producers " << producers.size() << " started.\n";

    for (auto& producer : producers) {
        // join 等待 producer 线程执行结束。
        // 必须在 shutdown 前等待所有 producer 完成，否则还有 producer 可能继续 push。
        producer.join();
    }
    std::cout << std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start).count() << "All producers joined.\n";
    // 通知所有等待中的 consumer：不会再有新的任务了。
    // ThreadSafeQueue::wait_and_pop 会先处理队列里剩余的任务；
    // 当队列为空且 shutdown 后，它返回 false，使 consumer 退出循环。
    queue.shutdown();

    for (auto& consumer : consumers) {
        // 等待 consumer 完成剩余任务并退出。
        // join 之后，main 再读取 stats 就不会和 consumer 写 stats 发生并发访问。
        consumer.join();
    }
    std::cout << std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start).count() << "All consumers joined.\n";

    const auto end = std::chrono::steady_clock::now();

    // duration_cast 是 C++11 特性，用于把 chrono duration 转换成指定单位。
    // 这里把 steady_clock 的耗时转换成毫秒，便于打印。
    const auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        end - start);

    std::uint64_t total_checksum = 0;
    for (int id = 0; id < consumer_count; ++id) {
        total_checksum += stats[id].checksum;
        std::cout << "[consumer " << id << "] total items = "
                  << stats[id].items << ", checksum = "
                  << stats[id].checksum << '\n';
    }

    std::cout << "produced = " << produced_count.load()
              << ", consumed = " << consumed_count.load() << '\n';
    std::cout << "total checksum = " << total_checksum << '\n';
    std::cout << "elapsed = " << elapsed_ms.count() << " ms\n";

    // 退出码约定：0 表示成功，非 0 表示失败。
    // 如果生成数量和消费数量不同，说明有任务丢失或统计逻辑有问题。
    return produced_count.load() == consumed_count.load() ? 0 : 1;
}
