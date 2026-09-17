#pragma once

#include <entt/entity/registry.hpp>

#include "tank/physics/obstacle_world.hpp"
#include "tank/physics/oriented_box.hpp"

namespace tank::sim {

// Moves every ProjectileState entity, bounces it off walls (physics::Reflect, same law used
// everywhere else), applies damage and destroys itself on hitting a tank, and expires it on
// lifespan/bounce-limit. Two deliberate differences from the original, both improvements rather
// than exact-fidelity ports:
//   - Wall collision is tested against the *actual* this-tick movement segment (old pos -> new
//     pos), not a fixed short visual-length ray - this closes a tunneling gap the original had
//     for fast projectiles vs. thin geometry.
//   - Tank hits are tested the same way (against the movement segment, all 4 box edges), rather
//     than relying on a separate driving loop external to this system.
// The original's "kill a projectile that bounces within its first ~10 ticks" quirk and its
// "use the ray from the tank's spawn point during a brief post-spawn window" rule are both
// preserved via ProjectileState::spawn_immunity_sec (also used to exempt only the owner tank
// from taking damage during that same brief window, since the original doesn't allow a
// projectile to instantly kill the tank that just fired it).
class ProjectileSystem {
public:
    void Update(entt::registry& registry, const physics::ObstacleWorld& world, const physics::OrientedBoxCache& box_cache,
                float dt);
};

}  // namespace tank::sim
