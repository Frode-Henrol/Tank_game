#pragma once

#include <entt/entity/registry.hpp>

#include "tank/ai/world_query.hpp"

namespace tank::ai {

// Drives every entity with an AIControlled component by writing MovementIntent/AimIntent/
// FireIntent components for the sim module's systems to consume - it never calls into a
// concrete unit type (there isn't one) and never mutates Transform/Health/etc. directly.
//
// The Idle/Patrol/Defend/Attack/Dodge state machine and pathfinding are M2a scope ("dumb but
// correct"); real A* pathfinding via WorldQuery::Navigation(). Wander is reserved for
// personalities with random_movement=true, added with M3's data-driven AIPersonality - the base
// FSM here never transitions into it on its own.
//
// Targeting/firing (see targeting.hpp/UpdateTargetingAndFiring in the .cpp) is M2b: intercept-
// lead aim for a moving target, an aiming-inaccuracy cone, and a shoot-safety gate built on
// ray-bounce shot prediction (refuses to fire if the predicted path passes too close to a mine,
// self, or any other living unit - not just allies, matching the original). Isolated as its own
// unit of work because predicted physics must track real physics exactly, or AI accuracy
// silently degrades - the single most bug-prone part of the whole port.
class BehaviorSystem {
public:
    void Update(entt::registry& registry, WorldQuery& world, float delta_time_sec);
};

}  // namespace tank::ai
