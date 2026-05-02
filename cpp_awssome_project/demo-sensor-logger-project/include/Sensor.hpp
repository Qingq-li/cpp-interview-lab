#pragma once

#include "SensorData.hpp"
#include "ThreadSafeQueue.hpp"

#include <atomic>
#include <chrono>
#include <random>
#include <string>
#include <thread>
#include <vector>

class Sensor {
public:
    Sensor(std::string name,
           SensorType type,
           std::chrono::milliseconds period,
           ThreadSafeQueue<SensorData>& output_queue);
    virtual ~Sensor();

    Sensor(const Sensor&) = delete;
    Sensor& operator=(const Sensor&) = delete;

    void start();
    void stop();
    const std::string& name() const;

protected:
    virtual std::vector<double> generateValues(std::mt19937& rng) = 0;

private:
    void run();

    std::string name_;
    SensorType type_;
    std::chrono::milliseconds period_;
    ThreadSafeQueue<SensorData>& output_queue_;
    std::thread worker_;
    std::atomic<bool> running_{false};
};

class CameraSensor final : public Sensor {
public:
    explicit CameraSensor(ThreadSafeQueue<SensorData>& output_queue);

private:
    std::vector<double> generateValues(std::mt19937& rng) override;
};

class RadarSensor final : public Sensor {
public:
    explicit RadarSensor(ThreadSafeQueue<SensorData>& output_queue);

private:
    std::vector<double> generateValues(std::mt19937& rng) override;
};

class IMUSensor final : public Sensor {
public:
    explicit IMUSensor(ThreadSafeQueue<SensorData>& output_queue);

private:
    std::vector<double> generateValues(std::mt19937& rng) override;
};
