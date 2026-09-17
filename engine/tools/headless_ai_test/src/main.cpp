// Acceptance test for the "AI completely decoupled from unit classes" requirement: this binary
// links only tank::ai + tank::physics + tank::ecs (+ entt transitively) - notably NOT SDL3, and
// not any concrete unit/vehicle type. That this links and runs at all is itself part of the
// proof; the asserts below check today's (M0/M1) stub behavior and grow into real
// behavior/targeting fixtures as the M2 milestone lands.

#include <cassert>
#include <cstdio>

#include <entt/entt.hpp>

#include "tank/ai/behavior_system.hpp"
#include "tank/ai/world_query.hpp"
#include "tank/ecs/gameplay_components.hpp"

namespace {
struct FakeWorldQuery : tank::ai::WorldQuery {};
}  // namespace

int main() {
    entt::registry registry;
    FakeWorldQuery world;

    const auto enemy = registry.create();
    registry.emplace<tank::ecs::Transform>(enemy, tank::ecs::Vec2{100.0f, 100.0f}, 0.0f);
    registry.emplace<tank::ecs::AIControlled>(enemy);
    registry.emplace<tank::ecs::MovementIntent>(
        enemy, tank::ecs::MovementIntent{1.0f, 1.0f, true, 45.0f});

    tank::ai::BehaviorSystem behavior_system;
    behavior_system.Update(registry, world, 1.0f / 100.0f);

    const auto& intent = registry.get<tank::ecs::MovementIntent>(enemy);
    assert(intent.throttle == 0.0f);
    assert(intent.turn_axis == 0.0f);
    assert(!intent.has_turn_target);

    std::printf("headless_ai_test: OK (ai module builds/runs with zero SDL linked)\n");
    return 0;
}
