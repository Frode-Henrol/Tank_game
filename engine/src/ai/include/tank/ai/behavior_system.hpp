#pragma once

#include <entt/entity/registry.hpp>

#include "tank/ai/world_query.hpp"

namespace tank::ai {

// Drives every entity with an AIControlled component by writing MovementIntent/AimIntent/
// FireIntent components for the sim module's systems to consume - it never calls into a
// concrete unit type (there isn't one) and never mutates Transform/Health/etc. directly.
//
// The full behavior state machine (Idle/Patrol/Defend/Attack/Wander/Dodge) and targeting math
// land in M2a/M2b; this is currently a stub that exists to prove the module boundary compiles
// and links with zero SDL dependency (see tools/headless_ai_test).
class BehaviorSystem {
public:
    void Update(entt::registry& registry, WorldQuery& world, float delta_time_sec);
};

}  // namespace tank::ai
