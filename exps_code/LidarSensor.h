#pragma once

#include "Sensor.h"

// 继承自抽象基类的具体传感器。
// 这里模拟激光雷达输出“最近障碍物距离”。
class LidarSensor : public Sensor {
public:
    LidarSensor() : Sensor("Lidar") {}

    SensorData sample(int sequence) override {
        SensorData data;
        data.sensorName = name();
        data.sequence = sequence;
        data.primaryValue = 1.5 + (sequence % 5) * 0.4;
        return data;
    }
};
