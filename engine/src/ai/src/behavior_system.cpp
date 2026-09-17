#include "tank/ai/behavior_system.hpp"

#include "tank/ecs/gameplay_components.hpp"

namespace tank::ai {

void BehaviorSystem::Update(entt::registry& registry, WorldQuery& /*world*/, float /*delta_time_sec*/) {
    // Stub for M0/M1: every AI-controlled entity holds still. Real behavior (M2a) writes
    // MovementIntent/AimIntent/FireIntent from the Idle/Patrol/Defend/Attack/Wander/Dodge FSM.
    auto view = registry.view<tank::ecs::AIControlled>();
    for (auto entity : view) {
        if (auto* intent = registry.try_get<tank::ecs::MovementIntent>(entity)) {
            *intent = tank::ecs::MovementIntent{};
        }
    }
}

}  // namespace tank::ai
