# Gameplay simulation systems. Consumes Intent components written by either PlayerInputSystem
# (in app/) or the ai module - has no idea which one wrote them. No SDL dependency: sim only
# ever touches the ECS registry and takes delta_time as a plain float parameter, so it stays
# testable the same way `ai` does (see tools/headless_ai_test).

add_library(tank_sim STATIC
    src/movement_system.cpp
)
add_library(tank::sim ALIAS tank_sim)

target_include_directories(tank_sim PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_sim PUBLIC tank::ecs tank::physics)
