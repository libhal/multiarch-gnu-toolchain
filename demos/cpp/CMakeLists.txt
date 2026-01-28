cmake_minimum_required(VERSION 3.40)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_COLOR_DIAGNOSTICS ON)

project(demo LANGUAGES CXX)

add_executable(demo main.cpp)

if(${CMAKE_CROSSCOMPILING})
  message(STATUS "⏭️ Binary is not native, skipping build")
else()
  message(STATUS "🚀 Will launch demo after building")
endif(${CMAKE_CROSSCOMPILING})

add_custom_target(run_demo ALL DEPENDS demo COMMAND ${CMAKE_BINARY_DIR}/demo)

add_custom_target(copy_compile_commands ALL
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_BINARY_DIR}/compile_commands.json"
        "${CMAKE_SOURCE_DIR}/compile_commands.json"
        || ${CMAKE_COMMAND} -E true
    COMMENT "Copying compile_commands.json to source directory"
)
