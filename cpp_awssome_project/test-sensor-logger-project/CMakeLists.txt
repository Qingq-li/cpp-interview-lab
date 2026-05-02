cmake_minimum_required(VERSION 3.16)
project(test_sensor_logger_project)

set(CMAKE_CXX_STANDARD 17)
set (CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)

add_executable(ThreadSafeQueue src/ThreadSafeQueue.cpp)

target_include_directories(ThreadSafeQueue
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(ThreadSafeQueue PRIVATE Threads::Threads)

add_executable(MultiThreadUniquePtrDemo src/MultiThreadUniquePtrDemo.cpp)

target_include_directories(MultiThreadUniquePtrDemo
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(MultiThreadUniquePtrDemo PRIVATE Threads::Threads)

add_executable(ThreadPoolUniquePtrDemo src/ThreadPoolUniquePtrDemo.cpp)

target_include_directories(ThreadPoolUniquePtrDemo
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(ThreadPoolUniquePtrDemo PRIVATE Threads::Threads)
