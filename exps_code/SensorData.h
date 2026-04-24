#pragma once

#include <string>

// 用一个统一的数据结构承接不同传感器输出，避免示例代码过长。
// 真实项目里也可以继续往下拆成多个数据类型，或使用 std::variant。
struct SensorData {
    std::string sensorName;
    int sequence = 0;
    double primaryValue = 0.0;
    double secondaryValue = 0.0;
};
