cmake_minimum_required(VERSION 3.16) # 设置 CMake 最低版本要求

 
project(sensor_fusion_logger LANGUAGES CXX) # 定义项目名称和使用的编程语言

set(CMAKE_CXX_STANDARD 17) # 设置 C++ 标准为 C++17，启用结构化绑定等特性
set(CMAKE_CXX_STANDARD_REQUIRED ON) # 强制要求使用 C++17 标准
set(CMAKE_CXX_EXTENSIONS OFF) # 禁止使用编译器特定的扩展，确保代码的可移植性

add_executable(sensor_fusion_logger # 定义可执行文件及其源文件列表
    src/FusionEngine.cpp
    src/Logger.cpp
    src/Sensor.cpp
    src/main.cpp
)

target_include_directories(sensor_fusion_logger # 设置包含目录，供编译器查找头文件
    PRIVATE # 仅对当前目标可见
        ${CMAKE_CURRENT_SOURCE_DIR}/include # 包含项目的 include 目录
)

target_compile_options(sensor_fusion_logger # 设置编译选项，启用警告以提高代码质量
    PRIVATE
        -Wall # 启用所有警告
        -Wextra # 启用额外的警告
        -Wpedantic  # 启用严格的标准兼容性警告
)

find_package(Threads REQUIRED) #
target_link_libraries(sensor_fusion_logger PRIVATE Threads::Threads)

enable_testing()

add_executable(thread_safe_queue_test
    tests/ThreadSafeQueueTest.cpp
)

target_include_directories(thread_safe_queue_test
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(thread_safe_queue_test
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

target_link_libraries(thread_safe_queue_test PRIVATE Threads::Threads)

add_test(NAME thread_safe_queue_test COMMAND thread_safe_queue_test)
