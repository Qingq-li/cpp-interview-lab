#include "FusionEngine.hpp"
#include "Logger.hpp"
#include "Sensor.hpp"
#include "SensorData.hpp"
#include "ThreadSafeQueue.hpp"

#include <chrono>
#include <memory>
#include <thread>
#include <vector>

int main() {
    ThreadSafeQueue<SensorData> sensor_queue;
    Logger logger;
    FusionEngine fusion(sensor_queue, logger);

    logger.start();
    fusion.start();

    std::vector<std::unique_ptr<Sensor>> sensors;
    sensors.push_back(std::make_unique<IMUSensor>(sensor_queue));
    sensors.push_back(std::make_unique<RadarSensor>(sensor_queue));
    sensors.push_back(std::make_unique<CameraSensor>(sensor_queue));

    logger.log("[main] starting sensors");
    for (auto& sensor : sensors) {
        logger.log("[main] start " + sensor->name());
        sensor->start();
    }

    std::this_thread::sleep_for(std::chrono::seconds(10));

    logger.log("[main] stopping sensors");
    for (auto& sensor : sensors) {
        sensor->stop();
        logger.log("[main] stopped " + sensor->name());
    }

    fusion.stop();
    logger.stop();

    return 0;
}
