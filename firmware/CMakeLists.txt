cmake_minimum_required(VERSION 3.20.0)

set(BOARD_ROOT ${CMAKE_CURRENT_SOURCE_DIR})
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(jrwatch_fw)

target_sources(app PRIVATE
  src/main.c
  src/ble.c
  src/motion.c
  src/ui.c
  src/power.c
)
target_include_directories(app PRIVATE src)
