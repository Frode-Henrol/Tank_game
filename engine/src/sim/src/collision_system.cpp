#include "tank/sim/collision_system.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <vector>

#include "tank/ecs/gameplay_components.hpp"
#include "tank/physics/geometry.hpp"

namespace tank::sim {

using tank::ecs::CollisionShape;
using tank::ecs::Health;
using tank::ecs::PreviousPosition;
using tank::ecs::Transform;
using tank::ecs::TrackedMovement;
using tank::ecs::Vec2;

namespace {

void ExpandBounds(Vec2& min, Vec2& max, const std::array<Vec2, 4>& corners) {
    for (const auto& corner : corners) {
        min.x = std::min(min.x, corner.x);
        min.y = std::min(min.y, corner.y);
        max.x = std::max(max.x, corner.x);
        max.y = std::max(max.y, corner.y);
    }
}

}  // namespace

void WallCollisionSystem::Update(entt::registry& registry, const physics::ObstacleWorld& world, float dt) {
    auto view = registry.view<Transform, CollisionShape, TrackedMovement>();
    for (auto entity : view) {
        auto& transform = view.get<Transform>(entity);
        const auto& shape = view.get<CollisionShape>(entity);
        const auto& movement = view.get<TrackedMovement>(entity);

        const auto* previous = registry.try_get<PreviousPosition>(entity);
        const Vec2 previous_position = previous != nullptr ? previous->position : transform.position;

        const auto old_corners =
            physics::BoxCorners(*box_cache_, previous_position, shape.half_width, shape.half_height, transform.heading_deg);
        auto new_corners =
            physics::BoxCorners(*box_cache_, transform.position, shape.half_width, shape.half_height, transform.heading_deg);

        Vec2 swept_min = old_corners[0];
        Vec2 swept_max = old_corners[0];
        ExpandBounds(swept_min, swept_max, old_corners);
        ExpandBounds(swept_min, swept_max, new_corners);

        // --- Swept check: did any corner's path this tick cross a wall edge? A test that only
        // looks at where the box ended up can miss a wall entirely at certain approach angles
        // (the box "jumps" from fully outside to fully inside between two samples without any
        // single-frame edge overlap ever existing) - the exact tunneling bug class reported
        // against this port (and, per the original author, against early builds of the Python
        // version too).
        //
        // The fix is a *slide*, not a full revert to the previous position: remove only the
        // component of this tick's movement that points into the wall (along its normal),
        // keeping whatever component runs tangent to it. A full revert cancels tangential
        // movement too, which reads as the tank "sticking" to any wall it approaches at an
        // angle instead of gliding along it the way the original does (there, movement is never
        // reverted at all - the collision response only ever adds a push along the wall's
        // normal on top of wherever that tick's own move already put the tank, so a component of
        // motion parallel to the wall is never touched and naturally carries the tank along it).
        // Picks whichever corner/edge crossing is *closest to that corner's own starting point*,
        // not just the first one the broad-phase happens to visit - a box moving fast enough to
        // swallow a wall thinner than its own extent crosses BOTH the near and far edge of that
        // wall in the same sweep, and taking an arbitrary one of those (rather than the nearest,
        // i.e. the surface actually touched first) can pick the far edge's outward normal, which
        // points the "correction" further through the wall instead of back out of it.
        bool tunneled = false;
        float closest_dist_sq = std::numeric_limits<float>::infinity();
        Vec2 tunnel_normal{};
        world.QueryEdgesNear(
            swept_min, swept_max, /*include_pits=*/true,
            [&](std::size_t /*obstacle_index*/, const Vec2& wall_start, const Vec2& wall_end) {
                for (std::size_t i = 0; i < old_corners.size(); ++i) {
                    const auto intersection = physics::SegmentIntersection(old_corners[i], new_corners[i], wall_start, wall_end);
                    if (!intersection) {
                        continue;
                    }
                    const float dist_sq = (*intersection - old_corners[i]).LengthSquared();
                    if (dist_sq < closest_dist_sq) {
                        closest_dist_sq = dist_sq;
                        // Always the edge's second normal, matching the same clockwise-winding
                        // convention as the resting-overlap push-back below.
                        const auto [unused_normal, outward_normal] = physics::EdgeNormals(wall_start, wall_end);
                        (void)unused_normal;
                        tunnel_normal = outward_normal;
                        tunneled = true;
                    }
                }
            });

        if (tunneled) {
            const Vec2 delta = transform.position - previous_position;
            const float into_wall = delta.Dot(tunnel_normal);
            if (into_wall < 0.0f) {
                transform.position = previous_position + (delta - tunnel_normal * into_wall);
                new_corners = physics::BoxCorners(*box_cache_, transform.position, shape.half_width, shape.half_height,
                                                    transform.heading_deg);
            }
        }

        // --- Direct overlap check at the (possibly-reverted) resting position: handles being
        // pressed flush against a wall by something other than this tick's own movement (e.g.
        // tank-tank repulsion), which the sweep above can't see (old == new position; a
        // zero-length "sweep" never intersects anything). ---
        const auto edges = physics::BoxEdges(new_corners);
        Vec2 rest_min = new_corners[0];
        Vec2 rest_max = new_corners[0];
        ExpandBounds(rest_min, rest_max, new_corners);

        bool resolved = false;
        world.QueryEdgesNear(rest_min, rest_max, /*include_pits=*/true,
                              [&](std::size_t /*obstacle_index*/, const Vec2& wall_start, const Vec2& wall_end) {
                                  if (resolved) {
                                      return;
                                  }
                                  for (const auto& [a, b] : edges) {
                                      if (physics::SegmentIntersection(a, b, wall_start, wall_end)) {
                                          const auto [unused_normal, outward_normal] =
                                              physics::EdgeNormals(wall_start, wall_end);
                                          (void)unused_normal;
                                          const float push_magnitude = movement.max_speed * dt;
                                          transform.position += outward_normal * push_magnitude;
                                          resolved = true;
                                          break;
                                      }
                                  }
                              });
    }
}

namespace {

// self is pushed away from other_pos - mirrors the original's apply_repulsion(self, other).
void ApplyRepulsion(Transform& self_transform, const Vec2& other_pos, float dt, float push_strength = 1.0f) {
    Vec2 delta = self_transform.position - other_pos;
    const float dist_sq = delta.LengthSquared();

    Vec2 direction;
    if (dist_sq < 1e-9f) {
        // Exactly-overlapping centers: the original picks a uniform-random direction; in
        // practice two entities never land on the exact same float position, so a fixed
        // fallback direction is an adequate (and simpler) substitute for this degenerate case.
        direction = Vec2{1.0f, 0.0f};
    } else {
        direction = delta * (1.0f / std::sqrt(dist_sq));
    }
    const Vec2 perpendicular{-direction.y, direction.x};

    const float repulsion_distance = push_strength * dt * 120.0f;
    const float perpendicular_strength = 0.2f * repulsion_distance;

    self_transform.position += direction * repulsion_distance + perpendicular * perpendicular_strength;
}

}  // namespace

void TankRepulsionSystem::Update(entt::registry& registry, float dt) {
    auto view = registry.view<Transform, CollisionShape>();
    const std::vector<entt::entity> entities(view.begin(), view.end());

    for (std::size_t i = 0; i < entities.size(); ++i) {
        for (std::size_t j = i + 1; j < entities.size(); ++j) {
            auto& transform_a = registry.get<Transform>(entities[i]);
            auto& transform_b = registry.get<Transform>(entities[j]);
            const auto& shape_a = registry.get<CollisionShape>(entities[i]);
            const auto& shape_b = registry.get<CollisionShape>(entities[j]);

            const float radius_a = std::max(shape_a.half_width, shape_a.half_height);
            const float radius_b = std::max(shape_b.half_width, shape_b.half_height);
            const float combined_radius = radius_a + radius_b;

            const Vec2 delta = transform_a.position - transform_b.position;
            if (delta.LengthSquared() >= combined_radius * combined_radius) {
                continue;
            }

            // A dead tank's wreck still physically blocks/pushes the living, matching the
            // original (make_dead() only disables move()/rotate()/shoot(), never removes the
            // hitbox) - so it isn't skipped from the overlap check above, only from being
            // shoved around itself: a corpse doesn't get pushed by what it's blocking.
            const auto* health_a = registry.try_get<Health>(entities[i]);
            const auto* health_b = registry.try_get<Health>(entities[j]);
            const bool alive_a = health_a == nullptr || health_a->current > 0.0f;
            const bool alive_b = health_b == nullptr || health_b->current > 0.0f;

            if (alive_a) {
                ApplyRepulsion(transform_a, transform_b.position, dt);
            }
            if (alive_b) {
                ApplyRepulsion(transform_b, transform_a.position, dt);
            }
        }
    }
}

}  // namespace tank::sim
