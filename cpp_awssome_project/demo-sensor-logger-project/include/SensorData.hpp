#pragma once

#include <chrono>
#include <string>
#include <vector>

enum class SensorType {
    Camera,
    Radar,
    IMU,
    GPS
};

struct SensorData {
    SensorType type;
    double timestamp;
    std::vector<double> values;
};

inline const char* toString(SensorType type) {
    switch (type) {
    case SensorType::Camera:
        return "Camera";
    case SensorType::Radar:
        return "Radar";
    case SensorType::IMU:
        return "IMU";
    case SensorType::GPS:
        return "GPS";
    }

    return "Unknown";
}

inline double currentTimestampSeconds() {
    using Clock = std::chrono::steady_clock;
    const auto now = Clock::now().time_since_epoch();
    return std::chrono::duration<double>(now).count();
}
