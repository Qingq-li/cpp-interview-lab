#pragma once

#include "Sensor.h"
#include "SensorData.h"
#include "ThreadSafeQueue.h"

#include <chrono>
#include <iostream>
#include <memory>
#include <thread>
#include <utility>
#include <vector>

// 这个类负责把“传感器线程 + 处理线程”组织起来。
// 重点是结构清晰，而不是做复杂功能。
class RobotProcessingSystem {
public:
    explicit RobotProcessingSystem(std::vector<std::unique_ptr<Sensor>> sensors)
        : sensors_(std::move(sensors)) {}

    void run() {
        startSensorThreads();
        startProcessingThread();
        joinAll();
    }

private:
    void startSensorThreads() {
        for (auto& sensor : sensors_) {
            Sensor* rawSensor = sensor.get();

            // 每个传感器单独开一个线程，统一走基类接口 sample()。
            sensorThreads_.emplace_back([this, rawSensor] {
                for (int seq = 1; seq <= 5; ++seq) {
                    SensorData data = rawSensor->sample(seq);
                    queue_.push(std::move(data));

                    std::this_thread::sleep_for(std::chrono::milliseconds(120));
                }
            });
        }
    }

    void startProcessingThread() {
        processingThread_ = std::thread([this] {
            int closedSensors = 0;
            const int totalSensors = static_cast<int>(sensors_.size());

            while (true) {
                auto data = queue_.waitAndPop();
                if (!data.has_value()) {
                    break;
                }

                process(*data);

                // 这里只是为了让示例停止条件简单清楚：
                // 每个传感器各发 5 条数据，因此 seq == 5 可视为该传感器收尾。
                if (data->sequence == 5) {
                    ++closedSensors;
                    if (closedSensors == totalSensors) {
                        queue_.close();
                    }
                }
            }
        });
    }

    void process(const SensorData& data) {
        if (data.sensorName == "Lidar") {
            std::cout
                << "[Processor] 传感器: " << data.sensorName
                << ", 序号: " << data.sequence
                << ", 最近障碍物距离: " << data.primaryValue << " m\n";
            return;
        }

        if (data.sensorName == "IMU") {
            std::cout
                << "[Processor] 传感器: " << data.sensorName
                << ", 序号: " << data.sequence
                << ", 角速度: " << data.primaryValue
                << ", 加速度: " << data.secondaryValue << '\n';
        }
    }

    void joinAll() {
        for (auto& thread : sensorThreads_) {
            thread.join();
        }

        if (processingThread_.joinable()) {
            processingThread_.join();
        }
    }

    std::vector<std::unique_ptr<Sensor>> sensors_;
    ThreadSafeQueue<SensorData> queue_;
    std::vector<std::thread> sensorThreads_;
    std::thread processingThread_;
};
