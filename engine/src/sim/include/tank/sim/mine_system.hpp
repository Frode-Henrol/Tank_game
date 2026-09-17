#pragma once

#include <entt/entity/registry.hpp>

#include "tank/physics/obstacle_world.hpp"

namespace tank::sim {

// Handles both sides of mines: (1) MineDeployer + MineIntent on a unit spawns a MineState
// entity, gated by cooldown/limit; (2) every MineState entity's life cycle - auto-arm after a
// life timer, an enemy-proximity trigger that shortens the fuse (matches the original: only the
// *first* trigger shortens it, matching check_for_tank()'s "if not already started" guard),
// explosion (instant-kills tanks in radius, removes nearby Destructible obstacles by testing
// their corner points - the original's coarse-but-cheap approximation, preserved as-is), and a
// post-explosion linger delay before the entity is actually destroyed.
class MineSystem {
public:
    void Update(entt::registry& registry, physics::ObstacleWorld& world, float dt);
};

}  // namespace tank::sim
