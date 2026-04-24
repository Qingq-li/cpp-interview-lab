# 机器人传感器处理系统

这是一个刻意控制规模的小项目，用来同时练这些知识点：

- 抽象类
- 继承
- 多态
- template
- 多线程

## 文件说明

- `Sensor.h`
  定义抽象基类 `Sensor`
- `LidarSensor.h`
  激光雷达派生类
- `ImuSensor.h`
  IMU 派生类
- `SensorData.h`
  统一数据结构
- `ThreadSafeQueue.h`
  模板线程安全队列
- `ThreadPool.h`
  小线程池，负责统一调度任务
- `RobotProcessingSystem.h`
  第一版：传感器线程直接把数据交给处理线程
- `RobotProcessingWithThreadPool.h`
  升级版：传感器线程把处理逻辑投递到线程池
- `main.cpp`
  默认运行线程池版本

## 如何编译

```bash
g++ -std=c++17 -pthread exps_code/main.cpp -o exps_code/robot_demo
```

## 如何运行

```bash
./exps_code/robot_demo
```

## 学习时重点看什么

### 1. 抽象类

- `Sensor` 里有纯虚函数 `sample()`
- 说明“所有传感器都要提供采样能力”

### 2. 继承和多态

- `LidarSensor` 和 `ImuSensor` 都继承 `Sensor`
- `std::vector<std::unique_ptr<Sensor>>` 统一管理不同派生类对象

### 3. template

- `ThreadSafeQueue<T>` 说明并发队列逻辑可以复用到不同类型

### 4. 多线程

- 每个传感器一个线程负责采样
- 升级版里由线程池 worker 并发处理任务

### 5. 线程池

- `ThreadPool` 里维护一组常驻 worker 线程
- `submit()` 负责提交任务
- `waitUntilEmpty()` 负责等待当前任务做完

### 6. lambda

- 在线程池版本里，最值得看的代码是：

```cpp
pool_.submit([this, data]() {
    processLidar(data);
});
```

- `[this, data]` 是捕获列表
- `()` 是参数列表
- `{ processLidar(data); }` 是任务体
- 这段 lambda 的作用是：把“稍后要在线程池里执行的逻辑”包装成一个任务对象

### 7. RAII

- `std::unique_ptr`
- `std::lock_guard`
- `std::thread` 的 `join()`

## 建议先按这个顺序阅读

1. `Sensor.h`
   看抽象类接口怎么定义
2. `LidarSensor.h` / `ImuSensor.h`
   看派生类如何覆写 `sample()`
3. `ThreadSafeQueue.h`
   看模板和 `mutex + condition_variable`
4. `ThreadPool.h`
   看线程池的最小组成
5. `RobotProcessingWithThreadPool.h`
   看 lambda 怎么把任务投递给线程池
6. `main.cpp`
   看整个系统如何组装

## 代码里最重要的知识点

### 1. 为什么 `Sensor` 要有虚析构函数

- 因为我们通过 `std::unique_ptr<Sensor>` 持有派生类对象
- 如果基类析构函数不是 `virtual`，通过基类指针销毁派生类对象会有未定义行为

### 2. 为什么线程池任务类型是 `std::function<void()>`

- 因为线程池只关心“这是一段可执行逻辑”
- 不关心它来自雷达、IMU，还是别的模块
- 这是一种典型的解耦方式

### 3. 为什么 lambda 要按值捕获 `data`

- 因为任务不是立刻执行，而是稍后在线程池里执行
- 如果按引用捕获，外层局部变量可能已经失效
- 按值捕获更安全，也更符合这个示例的教学目的

### 4. 线程池比“每来一个任务就创建一个线程”好在哪里

- 线程创建和销毁有成本
- 线程池会复用已有线程
- 结构也更像真实工程里的任务调度模型

## 这个项目故意没有做的事

为了保证代码短小清楚，这里没有加入：

- `future`
- 更复杂的线程池
- 真实传感器驱动
- 错误恢复和日志框架

你先把这个版本完全看懂，再继续扩展会更稳。
