#pragma once

#include <optional>
#include <utility>
#include <vector>

#include "tank/ecs/vec2.hpp"
#include "tank/physics/obstacle_world.hpp"

// Targeting/prediction math (M2b): isolated from the behavior FSM (M2a) as its own unit of
// work, since predicted physics must track real physics exactly - or AI accuracy silently
// degrades - making this the single most bug-prone part of the whole port. Every function here
// is pure (no registry, no entity types), so it can be unit-tested directly against known
// geometry and directly compared against ProjectileSystem's real simulation for the same inputs.

namespace tank::ai {

using tank::ecs::Vec2;

// Closed-form intercept lead: where should a projectile (speed=projectile_speed, fired now from
// shooter_pos) aim to meet a target currently at target_pos moving at target_velocity (world
// units/sec; zero vector if stationary)? Solves the standard "intercept" quadratic (degrading to
// linear if the target and projectile speeds coincide); falls back to target_pos (no lead) if no
// positive-time solution exists (e.g. the target is moving away faster than the shot closes).
[[nodiscard]] Vec2 InterceptPoint(const Vec2& shooter_pos, float projectile_speed, const Vec2& target_pos,
                                    const Vec2& target_velocity);

struct PredictedRay {
    std::vector<std::pair<Vec2, Vec2>> segments;
    // Set if a bounce landed within `corner_margin` of a wall vertex - the single-edge
    // reflection model used here (and by the real projectile) is unreliable that close to a
    // corner (the real, discretized bounce can behave unpredictably), so prediction stops early
    // and flags the point for a widened safety check around it, rather than continuing to
    // predict a path that may not match what actually happens.
    std::optional<Vec2> ambiguous_corner;
};

// Walks the same reflection law real projectiles use (physics::Reflect) up to max_bounces,
// predicting where a shot fired from `start` in `direction` would travel. Mirrors
// ProjectileSystem's own wall-bounce loop (nearest-intersection-wins, pit obstacles excluded)
// but is purely a prediction - it never creates an entity or mutates anything.
[[nodiscard]] PredictedRay PredictBouncePath(const physics::ObstacleWorld& obstacles, const Vec2& start,
                                               const Vec2& direction, int max_bounces, float corner_margin = 20.0f,
                                               float max_segment_length = 2000.0f);

// True if `point` both projects onto segment (a, b) - not just near the infinite line through it
// - and is within `threshold` of it. The building block of the shoot-safety gate: "would this
// predicted ray segment pass close enough to X (a mine/ally/self/the target) to matter."
[[nodiscard]] bool IsPointNearSegment(const Vec2& a, const Vec2& b, const Vec2& point, float threshold);

}  // namespace tank::ai
