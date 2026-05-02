# Multi-thread Sensor Fusion Logger

一个用于学习现代 C++ 并发编程的小项目：多个模拟传感器在不同线程中产生数据，数据进入线程安全队列，融合线程消费数据并生成状态日志，日志线程异步输出。

```text
IMU / Radar / Camera threads
        |
        v
ThreadSafeQueue<SensorData>
        |
        v
FusionEngine thread
        |
        v
ThreadSafeQueue<std::string>
        |
        v
Logger thread
```

## 你会练到什么

- `std::thread`
- `std::mutex`
- `std::condition_variable`
- `std::atomic`
- RAII 风格的线程启动和退出
- `std::unique_ptr`
- `std::move`
- 模板类
- 接口和多态
- producer-consumer queue
- CMake
- 简单单元测试

## 项目结构

```text
.
├── CMakeLists.txt
├── include/
│   ├── FusionEngine.hpp
│   ├── Logger.hpp
│   ├── Sensor.hpp
│   ├── SensorData.hpp
│   ├── ThreadSafeQueue.hpp
│   └── Utils.hpp
├── src/
│   ├── FusionEngine.cpp
│   ├── Logger.cpp
│   ├── Sensor.cpp
│   └── main.cpp
└── tests/
    └── ThreadSafeQueueTest.cpp
```

## 设计思路

### 1. 数据流

传感器不直接调用融合逻辑，而是把 `SensorData` 推入队列：

```cpp
output_queue_.push(std::move(data));
```

这样传感器线程和融合线程之间只通过队列通信，模块耦合更低。

### 2. ThreadSafeQueue

`ThreadSafeQueue<T>` 是项目的核心基础设施。它用：

- `std::mutex` 保护内部 `std::queue<T>`
- `std::condition_variable` 让消费者在没有数据时睡眠
- `shutdown()` 唤醒所有等待线程，避免程序退出时卡死

重点看这个文件：

```text
include/ThreadSafeQueue.hpp
```

学习顺序建议：

1. 先看 `push(T item)`
2. 再看 `wait_and_pop(T& item)`
3. 最后看 `shutdown()`

### 3. Sensor

`Sensor` 是基类，负责通用线程生命周期：

- `start()` 创建 worker thread
- `stop()` 停止循环并 `join()`
- `run()` 周期性生成数据

具体传感器只需要实现：

```cpp
std::vector<double> generateValues(std::mt19937& rng) override;
```

当前实现了：

- `IMUSensor`: 100 Hz
- `RadarSensor`: 5 Hz
- `CameraSensor`: 10 Hz

### 4. FusionEngine

`FusionEngine` 从 `ThreadSafeQueue<SensorData>` 中阻塞读取数据：

```cpp
while (input_queue_.wait_and_pop(data)) {
    process(data);
    maybeLogStatus();
}
```

它维护一个简化的融合状态：

- 最新 IMU yaw
- 最新 Radar distance
- 最新 Camera confidence

每秒输出一次状态，并用 `std::atomic<int>` 统计不同传感器的消息数量。

### 5. Logger

`Logger` 自己也有一个 `ThreadSafeQueue<std::string>`。

融合线程调用：

```cpp
logger_.log(message);
```

日志线程负责真正输出到 `std::cout`。这样 FusionEngine 不会阻塞在 I/O 上。

## 构建和运行

```bash
cmake -S . -B build
cmake --build build
./build/sensor_fusion_logger
```

程序默认运行 10 秒，然后按顺序关闭：

1. 停止所有 sensor 线程
2. 停止 fusion 线程
3. 停止 logger 线程

示例输出：

```text
[main] starting sensors
[main] start IMU
[main] start Radar
[main] start Camera
[fusion] started
[fusion] status yaw=1.59 deg, radar_distance=72.89 m, camera_confidence=0.83 | counts: IMU=99, Radar=6, Camera=10
...
[fusion] final statistics: IMU messages=980, Radar messages=50, Camera messages=100
[fusion] stopped
```

## 运行测试

项目包含一个简单的队列测试，不依赖 GoogleTest 或 Catch2。

```bash
cmake --build build
cd build
ctest --output-on-failure
```

测试覆盖：

- FIFO 顺序
- 移动字符串数据
- `shutdown()` 能唤醒阻塞中的消费者

## 推荐学习路线

### 第一步：先读队列

读：

```text
include/ThreadSafeQueue.hpp
tests/ThreadSafeQueueTest.cpp
```

搞清楚为什么 `wait_and_pop()` 需要：

```cpp
cv_.wait(lock, [this] {
    return shutdown_ || !queue_.empty();
});
```

这里的 predicate 是为了处理 spurious wakeup，也就是线程可能没有真实数据也被唤醒。

### 第二步：读传感器线程

读：

```text
include/Sensor.hpp
src/Sensor.cpp
```

重点看：

- 为什么 `running_` 用 `std::atomic<bool>`
- 为什么析构函数里调用 `stop()`
- 为什么数据 push 时用 `std::move(data)`

### 第三步：读融合线程

读：

```text
include/FusionEngine.hpp
src/FusionEngine.cpp
```

重点看：

- `FusionEngine` 如何从队列中消费数据
- 如何按类型更新状态
- 如何每秒输出一次状态
- 为什么 `stop()` 里要调用 `input_queue_.shutdown()`

### 第四步：读异步 Logger

读：

```text
include/Logger.hpp
src/Logger.cpp
```

重点理解：业务线程只提交日志字符串，真正的 I/O 由 Logger 线程执行。

## 可以继续改进的方向

- 把日志写入文件，而不是只输出到 `std::cout`
- 给 `SensorData` 增加显式 copy/move constructor，观察拷贝和移动发生的时机
- 给每个 sensor 增加配置参数，例如频率、噪声范围、传感器名字
- 增加 GPS sensor
- 使用 GoogleTest 或 Catch2 扩展测试
- 用 signal handler 支持 Ctrl+C 优雅退出

## 面试时可以怎么讲

可以这样总结：

> I built a small multi-threaded C++ sensor pipeline to practice production-style C++ design. It includes producer-consumer queues, condition variables, atomic counters, polymorphic sensor interfaces, RAII-based thread management, and asynchronous logging. The structure resembles a simplified real-time robotics or situational-awareness backend.

这个项目适合用来练习 C++、Linux、多线程、实时系统、传感器数据处理和系统集成。
