#include "tank/ai/behavior_system.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <optional>
#include <random>

#include "tank/ecs/gameplay_components.hpp"

namespace tank::ai {

using tank::ecs::AimIntent;
using tank::ecs::AIControlled;
using tank::ecs::BehaviorState;
using tank::ecs::Faction;
using tank::ecs::FireIntent;
using tank::ecs::Health;
using tank::ecs::MovementIntent;
using tank::ecs::NavAgent;
using tank::ecs::ProjectileState;
using tank::ecs::Transform;
using tank::ecs::TrackedMovement;
using tank::ecs::Vec2;

namespace {

constexpr float kDegToRad = std::numbers::pi_v<float> / 180.0f;
constexpr float kRadToDeg = 180.0f / std::numbers::pi_v<float>;

constexpr float kPatrolRadius = 250.0f;
constexpr float kDistLeavePatrol = 450.0f;
constexpr float kDistLeaveDefend = 800.0f;
constexpr float kDistLeaveAttack = 200.0f;
constexpr float kDefendTimeSec = 5.0f;
constexpr float kMinDefendRingDist = 250.0f;
constexpr float kMaxDefendRingDist = 650.0f;
constexpr float kDistStartDodge = 60.0f;
constexpr float kDodgeCooldownSec = 1.5f;
constexpr float kWaypointReachedDist = 50.0f;
constexpr float kSteerTurnThresholdDeg = 45.0f;

std::mt19937& Rng() {
    static std::mt19937 rng{std::random_device{}()};
    return rng;
}

float WrapDegrees(float degrees) {
    float wrapped = std::fmod(degrees, 360.0f);
    if (wrapped < 0.0f) {
        wrapped += 360.0f;
    }
    return wrapped;
}

float ShortestAngleDelta(float from, float to) {
    float delta = std::fmod(to - from + 180.0f, 360.0f) - 180.0f;
    if (delta < -180.0f) {
        delta += 360.0f;
    }
    return delta;
}

// Steers toward `target`: picks forward or reverse (whichever needs less rotation, matching the
// original's move_to_node()), rotates toward the resulting heading, and only throttles once
// reasonably aligned so the tank doesn't drive sideways while still turning.
void SteerTowards(const Transform& transform, const Vec2& target, MovementIntent& intent) {
    const Vec2 to_target = target - transform.position;
    if (to_target.LengthSquared() < 1.0f) {
        intent.throttle = 0.0f;
        intent.has_turn_target = false;
        return;
    }

    const float target_heading = std::atan2(to_target.y, to_target.x) * kRadToDeg;
    const bool use_reverse = std::fabs(ShortestAngleDelta(transform.heading_deg, target_heading)) > 90.0f;
    const float desired_heading = use_reverse ? WrapDegrees(target_heading + 180.0f) : target_heading;

    intent.has_turn_target = true;
    intent.turn_towards_deg = desired_heading;

    const float alignment_diff = std::fabs(ShortestAngleDelta(transform.heading_deg, desired_heading));
    intent.throttle = (alignment_diff < kSteerTurnThresholdDeg) ? (use_reverse ? -1.0f : 1.0f) : 0.0f;
}

// Advances along NavAgent's current path, popping waypoints as they're reached. No-op (leaves
// MovementIntent untouched beyond the caller's reset) if the path is empty/exhausted.
void FollowPath(const Transform& transform, NavAgent& nav_agent, MovementIntent& intent) {
    if (nav_agent.path_index >= nav_agent.path.size()) {
        return;
    }
    if ((nav_agent.path[nav_agent.path_index] - transform.position).Length() < kWaypointReachedDist) {
        ++nav_agent.path_index;
        if (nav_agent.path_index >= nav_agent.path.size()) {
            return;
        }
    }
    SteerTowards(transform, nav_agent.path[nav_agent.path_index], intent);
}

void ClearPath(NavAgent* nav_agent) {
    if (nav_agent != nullptr) {
        nav_agent->path.clear();
        nav_agent->path_index = 0;
    }
}

bool PathExhausted(const NavAgent* nav_agent) {
    return nav_agent == nullptr || nav_agent->path_index >= nav_agent->path.size();
}

void SetPath(NavAgent& nav_agent, std::optional<std::vector<Vec2>> path) {
    if (path) {
        nav_agent.path = std::move(*path);
        nav_agent.path_index = 0;
    }
}

entt::entity FindNearestEnemy(entt::registry& registry, entt::entity self, int self_team, const Vec2& self_pos) {
    entt::entity best = entt::null;
    float best_dist_sq = std::numeric_limits<float>::infinity();
    for (auto candidate : registry.view<Transform, Faction, Health>()) {
        if (candidate == self) {
            continue;
        }
        if (registry.get<Faction>(candidate).team == self_team) {
            continue;
        }
        if (registry.get<Health>(candidate).current <= 0.0f) {
            continue;
        }
        const float dist_sq = (registry.get<Transform>(candidate).position - self_pos).LengthSquared();
        if (dist_sq < best_dist_sq) {
            best_dist_sq = dist_sq;
            best = candidate;
        }
    }
    return best;
}

// Nearest projectile whose direction is roughly (within ~72 degrees, matching the original's
// 0.3 dot-product tolerance) pointed back at `self_pos` - the original's "simple" dodge mode
// (as opposed to its bounce-aware "advanced" mode, which is M2b's ray-bounce-prediction scope).
std::optional<Vec2> FindNearestProjectileThreat(entt::registry& registry, const Vec2& self_pos, float max_dist) {
    std::optional<Vec2> best;
    float best_dist_sq = max_dist * max_dist;
    for (auto entity : registry.view<Transform, ProjectileState>()) {
        const auto& transform = registry.get<Transform>(entity);
        const auto& projectile = registry.get<ProjectileState>(entity);

        const Vec2 to_self = self_pos - transform.position;
        const float dist_sq = to_self.LengthSquared();
        if (dist_sq >= best_dist_sq || dist_sq < 1e-6f) {
            continue;
        }
        if (projectile.direction.Normalized().Dot(to_self.Normalized()) < 0.3f) {
            continue;  // Not headed roughly toward us.
        }
        best_dist_sq = dist_sq;
        best = transform.position;
    }
    return best;
}

void PickPatrolTarget(WorldQuery& world, const Transform& transform, const AIControlled& ai, NavAgent& nav_agent) {
    const auto candidates = world.Navigation().FindValidNodesNear(ai.spawn_position, kPatrolRadius);
    if (candidates.empty()) {
        return;
    }
    std::uniform_int_distribution<std::size_t> dist(0, candidates.size() - 1);
    SetPath(nav_agent, world.Navigation().FindPath(transform.position, candidates[dist(Rng())]));
}

// Approximates the original's keep_distance_behavior(): hold a ring of distance from the target,
// preferring ring nodes closest to self (so the tank doesn't path behind its target to reach a
// symmetric point on the ring).
void PickDefendRingTarget(WorldQuery& world, const Transform& transform, const Vec2& target_pos, NavAgent& nav_agent) {
    const auto candidates = world.Navigation().FindValidNodesNear(target_pos, kMaxDefendRingDist);
    std::vector<Vec2> ring;
    ring.reserve(candidates.size());
    for (const auto& node : candidates) {
        const float dist = (node - target_pos).Length();
        if (dist > kMinDefendRingDist && dist < kMaxDefendRingDist) {
            ring.push_back(node);
        }
    }
    if (ring.empty()) {
        return;
    }
    std::sort(ring.begin(), ring.end(), [&](const Vec2& a, const Vec2& b) {
        return (a - transform.position).LengthSquared() < (b - transform.position).LengthSquared();
    });
    const std::size_t pick_count = std::min<std::size_t>(20, ring.size());
    std::uniform_int_distribution<std::size_t> dist(0, pick_count - 1);
    SetPath(nav_agent, world.Navigation().FindPath(transform.position, ring[dist(Rng())]));
}

// Perpendicular escape point either side of the incoming threat's path, snapped to whichever
// valid node ends up farthest from the threat - approximates the original's dodge().
void PickDodgeTarget(WorldQuery& world, const Transform& transform, const Vec2& threat_pos, NavAgent& nav_agent) {
    const Vec2 away = (transform.position - threat_pos).Normalized();
    const Vec2 perpendicular{-away.y, away.x};

    Vec2 best_node = transform.position;
    float best_dist_sq = -1.0f;
    for (const Vec2& side : {perpendicular, perpendicular * -1.0f}) {
        for (const Vec2& node : world.Navigation().FindValidNodesNear(transform.position + side * 100.0f, 60.0f)) {
            const float dist_sq = (node - threat_pos).LengthSquared();
            if (dist_sq > best_dist_sq) {
                best_dist_sq = dist_sq;
                best_node = node;
            }
        }
    }
    if (best_dist_sq >= 0.0f) {
        SetPath(nav_agent, world.Navigation().FindPath(transform.position, best_node));
    }
}

}  // namespace

void BehaviorSystem::Update(entt::registry& registry, WorldQuery& world, float dt) {
    auto view = registry.view<Transform, AIControlled, Faction, MovementIntent, AimIntent, FireIntent>();
    for (auto entity : view) {
        auto& transform = view.get<Transform>(entity);
        auto& ai = view.get<AIControlled>(entity);
        const auto& faction = view.get<Faction>(entity);
        auto& movement_intent = view.get<MovementIntent>(entity);
        auto& aim_intent = view.get<AimIntent>(entity);
        auto& fire_intent = view.get<FireIntent>(entity);

        movement_intent = MovementIntent{};
        fire_intent.want_fire = false;

        // --- Targeting: direct-aim at the nearest living enemy, no lead/prediction, no
        // shoot-safety gate - that's all M2b scope. Runs unconditionally (even an immobile
        // turret-only unit still aims and fires). ---
        const entt::entity target = FindNearestEnemy(registry, entity, faction.team, transform.position);
        ai.targeted_unit = target;
        if (target != entt::null) {
            aim_intent.target = registry.get<Transform>(target).position;
            fire_intent.weapon_slot = 0;
            fire_intent.want_fire = true;
        }

        const auto* movement = registry.try_get<TrackedMovement>(entity);
        if (movement == nullptr || movement->max_speed <= 0.0f) {
            continue;  // Immobile (turret-only) unit: aims/fires above, never patrols/moves.
        }

        auto* nav_agent = registry.try_get<NavAgent>(entity);

        // --- Dodge: a global interrupt that can preempt any other state, matching the original. ---
        if (ai.dodge_cooldown_sec > 0.0f) {
            ai.dodge_cooldown_sec -= dt;
        }
        if (ai.state != BehaviorState::Dodge && ai.dodge_cooldown_sec <= 0.0f) {
            if (const auto threat = FindNearestProjectileThreat(registry, transform.position, kDistStartDodge)) {
                ai.state = BehaviorState::Dodge;
                ClearPath(nav_agent);
                if (nav_agent != nullptr) {
                    PickDodgeTarget(world, transform, *threat, *nav_agent);
                }
                ai.dodge_cooldown_sec = kDodgeCooldownSec;
            }
        }

        if (ai.state == BehaviorState::Dodge) {
            if (PathExhausted(nav_agent)) {
                ai.state = BehaviorState::Defending;
                ai.state_timer_sec = 0.0f;
            } else {
                FollowPath(transform, *nav_agent, movement_intent);
                continue;
            }
        }

        switch (ai.state) {
            case BehaviorState::Idle:
                ai.spawn_position = transform.position;
                ai.state = BehaviorState::Patrolling;
                [[fallthrough]];  // Immediately re-evaluate Patrolling's exit condition this same tick.

            case BehaviorState::Patrolling:
                if (PathExhausted(nav_agent) && nav_agent != nullptr) {
                    PickPatrolTarget(world, transform, ai, *nav_agent);
                }
                if (target != entt::null &&
                    (registry.get<Transform>(target).position - transform.position).Length() < kDistLeavePatrol) {
                    ai.state = BehaviorState::Defending;
                    ai.state_timer_sec = 0.0f;
                    ClearPath(nav_agent);
                }
                break;

            case BehaviorState::Defending: {
                if (ai.state_timer_sec <= 0.0f) {
                    ai.state_timer_sec = kDefendTimeSec;
                }
                ai.state_timer_sec -= dt;
                if (ai.state_timer_sec <= 0.0f) {
                    ai.state = BehaviorState::Attacking;
                    ClearPath(nav_agent);
                    break;
                }
                if (target == entt::null) {
                    break;
                }
                const Vec2 target_pos = registry.get<Transform>(target).position;
                if ((target_pos - transform.position).Length() > kDistLeaveDefend) {
                    ai.state = BehaviorState::Attacking;
                    ClearPath(nav_agent);
                    break;
                }
                if (PathExhausted(nav_agent) && nav_agent != nullptr) {
                    PickDefendRingTarget(world, transform, target_pos, *nav_agent);
                }
                break;
            }

            case BehaviorState::Attacking: {
                if (target == entt::null) {
                    break;
                }
                const Vec2 target_pos = registry.get<Transform>(target).position;
                if ((target_pos - transform.position).Length() < kDistLeaveAttack) {
                    ai.state = BehaviorState::Defending;
                    ai.state_timer_sec = 0.0f;
                    ClearPath(nav_agent);
                    break;
                }
                if (PathExhausted(nav_agent) && nav_agent != nullptr) {
                    SetPath(*nav_agent, world.Navigation().FindPath(transform.position, target_pos));
                }
                break;
            }

            case BehaviorState::Wander:
                // Reserved for personalities with random_movement=true (M3's data-driven
                // AIPersonality); the base FSM above never transitions into it.
                break;

            case BehaviorState::Dodge:
                break;  // Handled above; unreachable here.
        }

        if (nav_agent != nullptr) {
            FollowPath(transform, *nav_agent, movement_intent);
        }
    }
}

}  // namespace tank::ai
