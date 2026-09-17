# Proves the AI/SDL decoupling boundary at build time: tank::ai itself links only entt/ecs/
# physics - no SDL3, no rendering/audio/input library anywhere in ITS link graph (see
# src/ai/CMakeLists.txt). If a future change to the ai module ever required SDL, that library
# target would simply fail to compile/link, catching the regression immediately.
#
# This test tool additionally links tank::sim - purely to compare BehaviorSystem's ray-bounce
# shot *prediction* against ProjectileSystem's actual simulated bounce for the same scenario
# (see TestPredictedRayMatchesActualBounce). That's still consistent with the decoupling proof:
# tank::sim itself has zero SDL in its own dependency graph either (movement/collision/weapon/
# projectile logic only, same as ai), so this tool still links zero SDL end to end.

add_executable(headless_ai_test
    src/main.cpp
)

target_link_libraries(headless_ai_test PRIVATE
    tank::ai
    tank::physics
    tank::ecs
    tank::sim
)

add_test(NAME headless_ai_test COMMAND headless_ai_test)
