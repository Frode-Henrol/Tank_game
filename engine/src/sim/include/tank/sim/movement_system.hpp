#pragma once

#include <entt/entity/registry.hpp>

namespace tank::sim {

// Applies MovementIntent to every entity with a TrackedMovement component (today's only
// locomotion kind - tank-style forward/back + turn-in-place, no strafe). A future
// HolonomicMovement archetype (free 2D movement, e.g. infantry) gets its own sibling system
// rather than a branch in this one - see the component schema notes in gameplay_components.hpp.
class TrackedMovementSystem {
public:
    void Update(entt::registry& registry, float delta_time_sec);
};

}  // namespace tank::sim
