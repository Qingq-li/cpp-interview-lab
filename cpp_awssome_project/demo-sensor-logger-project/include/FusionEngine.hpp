#pragma once

#include "Logger.hpp"
#include "SensorData.hpp"
#include "ThreadSafeQueue.hpp"

#include <atomic>
#include <chrono>
#include <thread>

class FusionEngine {
public:
    FusionEngine(ThreadSafeQueue<SensorData>& input_queue, Logger& logger);
    ~FusionEngine();

    FusionEngine(const FusionEngine&) = delete;
    FusionEngine& operator=(const FusionEngine&) = delete;

    void start();
    void stop();

    int imuCount() const;
    int radarCount() const;
    int cameraCount() const;

private:
    void run();
    void process(const SensorData& data);
    void maybeLogStatus();
    void logFinalStatistics();

    ThreadSafeQueue<SensorData>& input_queue_;
    Logger& logger_;
    std::thread worker_;
    std::atomic<bool> running_{false};

    std::atomic<int> imu_count_{0};
    std::atomic<int> radar_count_{0};
    std::atomic<int> camera_count_{0};

    double latest_yaw_degrees_ = 0.0;
    double latest_radar_distance_meters_ = 0.0;
    double latest_camera_confidence_ = 0.0;
    std::chrono::steady_clock::time_point last_status_time_;
};
