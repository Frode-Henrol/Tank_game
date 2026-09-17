#pragma once

#include "tank/ai/nav_grid.hpp"
#include "tank/physics/obstacle_world.hpp"

// Read-only view of *static level* state the ai module is allowed to see - obstacle geometry and
// the precomputed navigation grid. Everything dynamic (other units, their Health/Faction,
// projectiles, mines) is read directly off the entt::registry passed into
// BehaviorSystem::Update(), the same way a PlayerInputSystem would - the ai module never needs a
// concrete unit/vehicle type to reason about any of it, and never links SDL3. See
// engine/src/ai/CMakeLists.txt for how that boundary is enforced, not just documented.

namespace tank::ai {

class WorldQuery {
public:
    virtual ~WorldQuery() = default;

    [[nodiscard]] virtual const physics::ObstacleWorld& Obstacles() const = 0;
    [[nodiscard]] virtual const NavGrid& Navigation() const = 0;
};

}  // namespace tank::ai
