#include "FusionEngine.hpp"

#include <iomanip>
#include <sstream>

FusionEngine::FusionEngine(ThreadSafeQueue<SensorData>& input_queue, Logger& logger)
    : input_queue_(input_queue),
      logger_(logger),
      last_status_time_(std::chrono::steady_clock::now()) {}

FusionEngine::~FusionEngine() {
    stop();
}

void FusionEngine::start() {
    bool expected = false;
    if (!running_.compare_exchange_strong(expected, true)) {
        return;
    }

    worker_ = std::thread(&FusionEngine::run, this);
}

void FusionEngine::stop() {
    bool expected = true;
    if (!running_.compare_exchange_strong(expected, false)) {
        return;
    }

    input_queue_.shutdown();

    if (worker_.joinable()) {
        worker_.join();
    }
}

int FusionEngine::imuCount() const {
    return imu_count_.load();
}

int FusionEngine::radarCount() const {
    return radar_count_.load();
}

int FusionEngine::cameraCount() const {
    return camera_count_.load();
}

void FusionEngine::run() {
    logger_.log("[fusion] started");

    SensorData data;
    while (input_queue_.wait_and_pop(data)) {
        process(data);
        maybeLogStatus();
    }

    logFinalStatistics();
    logger_.log("[fusion] stopped");
}

void FusionEngine::process(const SensorData& data) {
    switch (data.type) {
    case SensorType::IMU:
        ++imu_count_;
        if (!data.values.empty()) {
            latest_yaw_degrees_ = data.values[0];
        }
        break;
    case SensorType::Radar:
        ++radar_count_;
        if (!data.values.empty()) {
            latest_radar_distance_meters_ = data.values[0];
        }
        break;
    case SensorType::Camera:
        ++camera_count_;
        if (!data.values.empty()) {
            latest_camera_confidence_ = data.values[0];
        }
        break;
    case SensorType::GPS:
        break;
    }
}

void FusionEngine::maybeLogStatus() {
    const auto now = std::chrono::steady_clock::now();
    if (now - last_status_time_ < std::chrono::seconds(1)) {
        return;
    }

    last_status_time_ = now;

    std::ostringstream stream;
    stream << std::fixed << std::setprecision(2)
           << "[fusion] status "
           << "yaw=" << latest_yaw_degrees_ << " deg, "
           << "radar_distance=" << latest_radar_distance_meters_ << " m, "
           << "camera_confidence=" << latest_camera_confidence_
           << " | counts: "
           << "IMU=" << imu_count_.load() << ", "
           << "Radar=" << radar_count_.load() << ", "
           << "Camera=" << camera_count_.load();

    logger_.log(stream.str());
}

void FusionEngine::logFinalStatistics() {
    std::ostringstream stream;
    stream << "[fusion] final statistics: "
           << "IMU messages=" << imu_count_.load() << ", "
           << "Radar messages=" << radar_count_.load() << ", "
           << "Camera messages=" << camera_count_.load();

    logger_.log(stream.str());
}
