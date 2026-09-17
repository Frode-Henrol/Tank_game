# Generic fixed-timestep application shell: owns the window, current State, and the single
# main loop every state (including menus/countdown/info-screen) ticks from - no blocking
# `while True` sub-loops with their own ad-hoc clocks like the original had.

add_library(tank_core STATIC
    src/app.cpp
)
add_library(tank::core ALIAS tank_core)

target_include_directories(tank_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_core PUBLIC tank::ecs tank::render SDL3::SDL3)
