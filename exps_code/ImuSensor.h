#pragma once

#include "Sensor.h"

// IMU 示例：这里模拟角速度和加速度。
class ImuSensor : public Sensor {
public:
    ImuSensor() : Sensor("IMU") {}

    SensorData sample(int sequence) override {
        SensorData data;
        data.sensorName = name();
        data.sequence = sequence;
        data.primaryValue = 0.8 + sequence * 0.15;
        data.secondaryValue = 9.6 + (sequence % 3) * 0.1;
        return data;
    }
};
