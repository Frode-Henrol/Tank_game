#include "tank/sim/projectile_system.hpp"

#include <algorithm>
#include <limits>
#include <vector>

#include "tank/ecs/gameplay_components.hpp"
#include "tank/physics/geometry.hpp"

namespace tank::sim {

using tank::ecs::CollisionShape;
using tank::ecs::Health;
using tank::ecs::ProjectileState;
using tank::ecs::Transform;
using tank::ecs::Vec2;

void ProjectileSystem::Update(entt::registry& registry, const physics::ObstacleWorld& world, float dt) {
    std::vector<entt::entity> to_destroy;

    auto view = registry.view<Transform, ProjectileState>();
    auto tank_view = registry.view<Transform, CollisionShape, Health>();

    for (auto entity : view) {
        auto& transform = view.get<Transform>(entity);
        auto& projectile = view.get<ProjectileState>(entity);

        if (projectile.spawn_immunity_sec > 0.0f) {
            projectile.spawn_immunity_sec -= dt;
        }

        // Original quirk: a projectile that has already bounced at least once, while still
        // within its post-spawn immunity window, self-destructs. (No explosion FX wiring here
        // yet - that lands with M4's animation pass.)
        if (projectile.bounce_count > 0 && projectile.spawn_immunity_sec > 0.0f) {
            to_destroy.push_back(entity);
            continue;
        }

        const Vec2 old_pos = transform.position;
        const Vec2 new_pos = old_pos + projectile.direction * (projectile.speed * dt);

        // --- Tank hits: a radius check (perpendicular distance from the tank's center to this
        // tick's movement segment, clamped to the segment) rather than a rotated-box-edge test -
        // one distance comparison per candidate tank instead of four segment intersections,
        // which is what actually matters at scale. Checked before wall bounce so a projectile
        // that kills a tank this tick never also bounces in the same tick. A dead tank is
        // deliberately NOT skipped here: its wreck still physically blocks/absorbs shots
        // (matching the original), it just can't take further damage or die again. ---
        bool hit_tank = false;
        for (auto tank_entity : tank_view) {
            if (tank_entity == projectile.owner && projectile.spawn_immunity_sec > 0.0f) {
                continue;  // Can't instantly kill the tank that just fired this shot.
            }
            auto& tank_health = tank_view.get<Health>(tank_entity);
            const auto& tank_transform = tank_view.get<Transform>(tank_entity);
            const auto& tank_shape = tank_view.get<CollisionShape>(tank_entity);
            const float hit_radius = std::max(tank_shape.half_width, tank_shape.half_height);

            if (physics::IsBetweenSegment(old_pos, new_pos, tank_transform.position) &&
                physics::DistanceToLine(old_pos, new_pos, tank_transform.position) < hit_radius) {
                if (tank_health.current > 0.0f) {
                    tank_health.current -= projectile.damage * tank_health.damage_multiplier;
                }
                hit_tank = true;
                break;
            }
        }

        if (hit_tank) {
            to_destroy.push_back(entity);
            continue;
        }

        // --- Wall bounce: nearest intersection along the movement segment wins. ---
        bool bounced = false;
        float closest_dist_sq = std::numeric_limits<float>::infinity();
        Vec2 closest_point{};
        Vec2 closest_normal{};

        const Vec2 seg_min{std::min(old_pos.x, new_pos.x), std::min(old_pos.y, new_pos.y)};
        const Vec2 seg_max{std::max(old_pos.x, new_pos.x), std::max(old_pos.y, new_pos.y)};

        world.QueryEdgesNear(
            seg_min, seg_max, /*include_pits=*/false,
            [&](std::size_t /*obstacle_index*/, const Vec2& wall_start, const Vec2& wall_end) {
                const auto intersection = physics::SegmentIntersection(old_pos, new_pos, wall_start, wall_end);
                if (!intersection) {
                    return;
                }
                const float dist_sq = (*intersection - old_pos).LengthSquared();
                if (dist_sq < closest_dist_sq) {
                    closest_dist_sq = dist_sq;
                    closest_point = *intersection;
                    const auto [normal1, normal2] = physics::EdgeNormals(wall_start, wall_end);
                    closest_normal = projectile.direction.Dot(normal1) < 0.0f ? normal1 : normal2;
                    bounced = true;
                }
            });

        if (bounced) {
            projectile.direction = physics::Reflect(projectile.direction, closest_normal);
            transform.position = closest_point + projectile.direction * 0.1f;
            ++projectile.bounce_count;
            if (projectile.bounce_count >= projectile.bounce_limit) {
                to_destroy.push_back(entity);
                continue;
            }
        } else {
            transform.position = new_pos;
        }

        projectile.lifespan_sec -= dt;
        if (projectile.lifespan_sec <= 0.0f) {
            to_destroy.push_back(entity);
        }
    }

    for (auto entity : to_destroy) {
        registry.destroy(entity);
    }
}

}  // namespace tank::sim
