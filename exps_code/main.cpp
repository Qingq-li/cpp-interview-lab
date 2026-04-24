#include "ImuSensor.h"
#include "LidarSensor.h"
#include "RobotProcessingWithThreadPool.h"

#include <iostream>
#include <memory>
#include <utility>
#include <vector>

int main() {
    std::cout << "启动机器人传感器处理系统（线程池版本）...\n";

    // 使用基类指针容器统一管理不同类型的传感器，
    // 这是继承 + 多态在工程代码里很常见的用法。
    std::vector<std::unique_ptr<Sensor>> sensors;
    sensors.push_back(std::make_unique<LidarSensor>());
    sensors.push_back(std::make_unique<ImuSensor>());

    // 这里给线程池分配 3 个 worker。
    // 你可以把它理解成“预先创建好 3 个工人，等着拿任务干活”。
    RobotProcessingWithThreadPool system(std::move(sensors), 3);
    system.run();

    std::cout << "系统结束。\n";
    return 0;
}
