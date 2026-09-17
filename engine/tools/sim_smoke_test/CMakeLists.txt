# Deterministic, headless integration test for the M1 simulation pipeline (movement, wall
# collision, weapon/projectile fire+bounce+damage, mine deploy+explode). No SDL, no wall-clock
# or OS input dependency - every tick is driven by an explicit, fixed delta_time, so results are
# fully repeatable. This is the reliable alternative to manually driving the real windowed game
# with synthetic OS input (which proved unreliable to script from outside the process).

add_executable(sim_smoke_test
    src/main.cpp
)

target_link_libraries(sim_smoke_test PRIVATE
    tank::ecs
    tank::physics
    tank::content
    tank::sim
)

# Points at the existing Python project's assets so map-loading tests read the real map files.
target_compile_definitions(sim_smoke_test PRIVATE ASSET_ROOT="${CMAKE_SOURCE_DIR}/../tankgame")

add_test(NAME sim_smoke_test COMMAND sim_smoke_test)
