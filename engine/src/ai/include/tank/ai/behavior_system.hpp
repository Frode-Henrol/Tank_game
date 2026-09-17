#pragma once

#include <entt/entity/registry.hpp>

#include "tank/ai/world_query.hpp"

namespace tank::ai {

// Drives every entity with an AIControlled component by writing MovementIntent/AimIntent/
// FireIntent components for the sim module's systems to consume - it never calls into a
// concrete unit type (there isn't one) and never mutates Transform/Health/etc. directly.
//
// M2a scope ("dumb but correct"): the Idle/Patrol/Defend/Attack/Dodge state machine, real A*
// pathfinding (WorldQuery::Navigation()), and direct-aim targeting (always the current position
// of the nearest living enemy, no lead/prediction, no shoot-safety gate). Wander is reserved for
// personalities with random_movement=true, added with M3's data-driven AIPersonality - the base
// FSM here never transitions into it on its own. Intercept-lead targeting, ray-bounce shot
// prediction, and the mine/self/ally shoot-safety gate are M2b's follow-up scope, isolated
// separately because that's the single most bug-prone part of the whole port (predicted physics
// must track real physics exactly or AI accuracy silently degrades).
class BehaviorSystem {
public:
    void Update(entt::registry& registry, WorldQuery& world, float delta_time_sec);
};

}  // namespace tank::ai
