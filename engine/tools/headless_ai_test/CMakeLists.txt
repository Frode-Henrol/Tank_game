# Proves the AI/SDL decoupling boundary at build time: this executable links tank::ai +
# tank::physics + tank::ecs + entt and NOTHING else - no SDL3, no rendering/audio/input library
# anywhere in its link graph. If a future change to the ai module ever required SDL, this
# target would simply fail to compile/link, catching the regression immediately rather than it
# being discovered later. Fixture-driven behavior/targeting assertions are added as part of the
# M2 milestone; today this proves the target builds, links with zero SDL, and runs.

add_executable(headless_ai_test
    src/main.cpp
)

target_link_libraries(headless_ai_test PRIVATE
    tank::ai
    tank::physics
    tank::ecs
)

add_test(NAME headless_ai_test COMMAND headless_ai_test)
