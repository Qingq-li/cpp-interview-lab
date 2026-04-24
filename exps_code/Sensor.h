#pragma once

#include "SensorData.h"

#include <string>
#include <utility>

// 抽象类：定义所有传感器共同遵守的接口。
// 这正是“统一抽象 + 不同实现”的典型用法。
class Sensor {
public:
    explicit Sensor(std::string name) : name_(std::move(name)) {}
    virtual ~Sensor() = default;

    const std::string& name() const {
        return name_;
    }

    // 纯虚函数：派生类必须实现自己的采样逻辑。
    virtual SensorData sample(int sequence) = 0;

private:
    std::string name_;
};
