#include "Sensor.hpp"

#include "Utils.hpp"

#include <chrono>
#include <random>
#include <utility>

Sensor::Sensor(std::string name,
               SensorType type,
               std::chrono::milliseconds period,
               ThreadSafeQueue<SensorData>& output_queue)
    : name_(std::move(name)),
      type_(type),
      period_(period),
      output_queue_(output_queue) {}

Sensor::~Sensor() {
    stop();
}

void Sensor::start() {
    bool expected = false;
    if (!running_.compare_exchange_strong(expected, true)) {
        return;
    }

    worker_ = std::thread(&Sensor::run, this);
}

void Sensor::stop() {
    running_ = false;

    if (worker_.joinable()) {
        worker_.join();
    }
}

const std::string& Sensor::name() const {
    return name_;
}

void Sensor::run() {
    // Seed each sensor independently so their simulated values are not identical.
    std::random_device random_device;
    std::mt19937 rng(random_device());

    while (running_) {
        SensorData data{
            type_,
            currentTimestampSeconds(),
            generateValues(rng)
        };

        output_queue_.push(std::move(data));
        std::this_thread::sleep_for(period_);
    }
}

CameraSensor::CameraSensor(ThreadSafeQueue<SensorData>& output_queue)
    : Sensor("Camera", SensorType::Camera, std::chrono::milliseconds(100), output_queue) {}

std::vector<double> CameraSensor::generateValues(std::mt19937& rng) {
    std::uniform_real_distribution<double> confidence_distribution(0.80, 1.05);
    std::uniform_real_distribution<double> object_x_distribution(-45.0, 45.0);

    const double confidence = clampValue(confidence_distribution(rng), 0.0, 1.0);
    const double object_x_degrees = object_x_distribution(rng);

    return {confidence, object_x_degrees};
}

RadarSensor::RadarSensor(ThreadSafeQueue<SensorData>& output_queue)
    : Sensor("Radar", SensorType::Radar, std::chrono::milliseconds(200), output_queue) {}

std::vector<double> RadarSensor::generateValues(std::mt19937& rng) {
    std::uniform_real_distribution<double> distance_distribution(2.0, 120.0);
    std::uniform_real_distribution<double> velocity_distribution(-20.0, 35.0);

    const double distance_meters = clampValue(distance_distribution(rng), 0.0, 150.0);
    const double velocity_meters_per_second = velocity_distribution(rng);

    return {distance_meters, velocity_meters_per_second};
}

IMUSensor::IMUSensor(ThreadSafeQueue<SensorData>& output_queue)
    : Sensor("IMU", SensorType::IMU, std::chrono::milliseconds(10), output_queue) {}

std::vector<double> IMUSensor::generateValues(std::mt19937& rng) {
    std::normal_distribution<double> yaw_rate_distribution(0.0, 2.0);
    std::normal_distribution<double> acceleration_distribution(0.0, 0.4);

    const double yaw_degrees = clampValue(yaw_rate_distribution(rng), -180.0, 180.0);
    const double acceleration_meters_per_second2 =
        clampValue(acceleration_distribution(rng), -16.0, 16.0);

    return {yaw_degrees, acceleration_meters_per_second2};
}
