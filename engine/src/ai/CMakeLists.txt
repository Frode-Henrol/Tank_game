# This target is the enforcement point for "AI completely decoupled from unit classes": it
# links ONLY entt + tank_ecs + tank_physics - no SDL3 (rendering/audio/input) anywhere in its
# dependency graph, and no concrete unit/vehicle type. If any ai/ source file ever tries
# `#include <SDL3/SDL.h>`, the build fails, because SDL3's include directories are never added
# to this target. tools/headless_ai_test builds and runs this module in an executable that
# links zero SDL libraries at all, as the concrete, checkable acceptance test for this
# boundary (see the M2 milestone in the project plan).

add_library(tank_ai STATIC
    src/behavior_system.cpp
    src/nav_grid.cpp
)
add_library(tank::ai ALIAS tank_ai)

target_include_directories(tank_ai PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_ai PUBLIC tank::ecs tank::physics)
