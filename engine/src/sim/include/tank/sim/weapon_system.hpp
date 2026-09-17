#pragma once

#include <entt/entity/registry.hpp>

namespace tank::sim {

// Turns FireIntent + AimIntent + WeaponMounts into spawned ProjectileState entities - has no
// idea whether the intent was written by PlayerInputSystem or the ai module. Handles cooldown,
// the optional magazine/reload model, and the per-owner concurrent-projectile cap, mirroring
// the original's firerate/mag_size/reload_time/projectile_limit rules.
class WeaponSystem {
public:
    void Update(entt::registry& registry, float dt);
};

}  // namespace tank::sim
