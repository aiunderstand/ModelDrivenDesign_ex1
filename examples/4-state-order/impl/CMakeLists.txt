cmake_minimum_required(VERSION 3.20)
project(order CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_library(shop STATIC
    src/order.cpp
    src/shipment.cpp
)
target_include_directories(shop PUBLIC include)
target_compile_options(shop PRIVATE -Wall -Wextra)

add_executable(demo src/demo.cpp)
target_link_libraries(demo PRIVATE shop)
