#include "tank/sim/weapon_system.hpp"

#include <unordered_map>

#include "tank/ecs/gameplay_components.hpp"

namespace tank::sim {

using tank::ecs::AimIntent;
using tank::ecs::FireIntent;
using tank::ecs::ProjectileState;
using tank::ecs::Transform;
using tank::ecs::Vec2;
using tank::ecs::WeaponMounts;

namespace {
// How far from the owner's center a projectile spawns, along the aim direction - must clear
// the owner's own collision box or it would immediately register as a self-hit. Matches the
// original's spawn_distance_from_middle.
constexpr float kSpawnOffset = 30.0f;
// Ticks of post-spawn immunity, expressed in seconds assuming a 100 Hz fixed step - matches the
// original's spawn_timer (10 ticks).
constexpr float kSpawnImmunitySec = 10.0f / 100.0f;
}  // namespace

void WeaponSystem::Update(entt::registry& registry, float dt) {
    std::unordered_map<entt::entity, int> alive_projectiles_by_owner;
    for (auto entity : registry.view<ProjectileState>()) {
        ++alive_projectiles_by_owner[registry.get<ProjectileState>(entity).owner];
    }

    auto view = registry.view<Transform, WeaponMounts, AimIntent, FireIntent>();
    for (auto entity : view) {
        const auto& transform = view.get<Transform>(entity);
        auto& mounts = view.get<WeaponMounts>(entity);
        const auto& aim = view.get<AimIntent>(entity);
        const auto& fire = view.get<FireIntent>(entity);

        for (auto& weapon : mounts.weapons) {
            if (weapon.cooldown_sec > 0.0f) {
                weapon.cooldown_sec -= dt;
            }
            if (weapon.reloading) {
                weapon.reload_timer_sec -= dt;
                if (weapon.reload_timer_sec <= 0.0f) {
                    weapon.reloading = false;
                    weapon.magazine_ammo = weapon.def.magazine_size;
                }
            }
        }

        if (!fire.want_fire || fire.weapon_slot >= mounts.weapons.size()) {
            continue;
        }
        auto& weapon = mounts.weapons[fire.weapon_slot];

        if (weapon.cooldown_sec > 0.0f || weapon.reloading) {
            continue;
        }
        if (weapon.def.magazine_size > 0 && weapon.magazine_ammo <= 0) {
            continue;
        }
        if (alive_projectiles_by_owner[entity] >= weapon.def.projectile_limit) {
            continue;
        }

        const Vec2 aim_direction = (aim.target - transform.position).Normalized();
        if (aim_direction.LengthSquared() == 0.0f) {
            continue;  // No valid aim point yet (e.g. degenerate target == position).
        }

        const auto projectile_entity = registry.create();
        registry.emplace<Transform>(projectile_entity, transform.position + aim_direction * kSpawnOffset, 0.0f);
        registry.emplace<ProjectileState>(
            projectile_entity, ProjectileState{entity, aim_direction, transform.position, weapon.def.projectile_speed,
                                                 0, weapon.def.bounce_limit, weapon.def.damage, 5.0f, kSpawnImmunitySec});

        weapon.cooldown_sec = weapon.def.fire_interval_sec;
        ++alive_projectiles_by_owner[entity];

        if (weapon.def.magazine_size > 0) {
            --weapon.magazine_ammo;
            if (weapon.magazine_ammo <= 0) {
                weapon.reloading = true;
                weapon.reload_timer_sec = weapon.def.reload_time_sec;
            }
        }
    }
}

}  // namespace tank::sim
