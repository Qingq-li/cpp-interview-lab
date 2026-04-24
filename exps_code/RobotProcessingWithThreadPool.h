#pragma once

#include "Sensor.h"
#include "SensorData.h"
#include "ThreadPool.h"

#include <chrono>
#include <iostream>
#include <memory>
#include <thread>
#include <utility>
#include <vector>

// 这个版本展示“传感器采样”和“数据处理”如何通过线程池解耦。
//
// 基本流程：
// 1. 每个传感器线程负责产生数据
// 2. 采样到数据后，不直接处理，而是投递到线程池
// 3. 线程池里的 worker 并发执行处理任务
class RobotProcessingWithThreadPool {
public:
    RobotProcessingWithThreadPool(std::vector<std::unique_ptr<Sensor>> sensors,
                                  std::size_t workerCount)
        : sensors_(std::move(sensors)), pool_(workerCount) {}

    void run() {
        startSensorThreads();
        joinSensorThreads();
        pool_.waitUntilEmpty();
        pool_.shutdown();
    }

private:
    void startSensorThreads() {
        for (auto& sensor : sensors_) {
            Sensor* rawSensor = sensor.get();

            sensorThreads_.emplace_back([this, rawSensor] {
                for (int seq = 1; seq <= 5; ++seq) {
                    SensorData data = rawSensor->sample(seq);
                    dispatchTask(std::move(data));

                    std::this_thread::sleep_for(std::chrono::milliseconds(120));
                }
            });
        }
    }

    void dispatchTask(SensorData data) {
        if (data.sensorName == "Lidar") {
            // 这一整段 [this, data]() { processLidar(data); } 是 lambda。
            // 它的作用是“把将来要执行的处理逻辑包装成一个任务”。
            //
            // [this, data]：
            // - this: 让 lambda 可以调用当前对象的成员函数
            // - data: 把本次采样结果按值捕获进去，保证任务稍后执行时数据仍然有效
            //
            // ()：这里没有额外参数
            // { processLidar(data); }：真正的任务逻辑
            pool_.submit([this, data]() {
                processLidar(data);
            });
            return;
        }

        pool_.submit([this, data]() {
            processImu(data);
        });
    }

    void processLidar(const SensorData& data) {
        std::cout
            << "[ThreadPool] 传感器: " << data.sensorName
            << ", 序号: " << data.sequence
            << ", 最近障碍物距离: " << data.primaryValue << " m\n";
    }

    void processImu(const SensorData& data) {
        std::cout
            << "[ThreadPool] 传感器: " << data.sensorName
            << ", 序号: " << data.sequence
            << ", 角速度: " << data.primaryValue
            << ", 加速度: " << data.secondaryValue << '\n';
    }

    void joinSensorThreads() {
        for (auto& thread : sensorThreads_) {
            if (thread.joinable()) {
                thread.join();
            }
        }
    }

    std::vector<std::unique_ptr<Sensor>> sensors_;
    ThreadPool pool_;
    std::vector<std::thread> sensorThreads_;
};
