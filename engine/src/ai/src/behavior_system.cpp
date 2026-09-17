#include "tank/ai/behavior_system.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <optional>
#include <random>

#include "tank/ai/targeting.hpp"
#include "tank/ecs/gameplay_components.hpp"

namespace tank::ai {

using tank::ecs::AimIntent;
using tank::ecs::AIControlled;
using tank::ecs::AIPersonalityTuning;
using tank::ecs::BehaviorState;
using tank::ecs::Faction;
using tank::ecs::FireIntent;
using tank::ecs::Health;
using tank::ecs::MineDeployer;
using tank::ecs::MineIntent;
using tank::ecs::MineState;
using tank::ecs::MovementIntent;
using tank::ecs::NavAgent;
using tank::ecs::ProjectileState;
using tank::ecs::Transform;
using tank::ecs::TrackedMovement;
using tank::ecs::Vec2;
using tank::ecs::WeaponMounts;

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

// M2b targeting/firing tuning. Fallback defaults for an entity with no AIPersonalityTuning
// component (M2's own test fixtures predate M3's data-driven personalities and still spawn
// units without one) - a real spawn always carries per-unit values from ai.json instead; see
// ResolveTuning() below.
constexpr bool kPredictiveTargeting = true;
constexpr int kPredictiveTargetingChance = 50;  // percent
constexpr float kAimingAngleDeg = 15.0f;        // inaccuracy cone half-width
constexpr float kAimJitterReRollSec = 1.5f;
constexpr float kSafeThresholdPx = 60.0f;   // don't shoot if the predicted ray passes this close to self/an ally/a mine
constexpr float kShootThresholdPx = 15.0f;  // only fire if the predicted ray passes this close to the actual target
constexpr float kDefaultProjectileSpeed = 300.0f;
constexpr int kDefaultBounceLimit = 1;
// Must match WeaponSystem's kSpawnOffset (weapon_system.cpp) - the shot-prediction ray needs to
// start where the projectile will actually spawn, both for accuracy and because starting the
// ray exactly at the tank's own center makes "am I near my own predicted ray" trivially true at
// distance zero (the ray's first segment starts AT that point), which would make the
// self-safety check refuse to ever fire. Offsetting the start ahead of the tank puts the tank
// itself behind the ray's start, correctly excluding it from IsBetweenSegment.
constexpr float kFireSpawnOffset = 30.0f;

// Per-entity tuning actually used by this file each tick, resolved once from an
// AIPersonalityTuning component if present, else the fallback constants above (which also
// cover PickDefendRingTarget's ring distances and PickDodgeTarget's escape-point search radius:
// the original hardcodes those directly in code rather than reading them from ai.json too, so
// there's nothing to resolve for them here).
struct ResolvedTuning {
    float patrol_radius = kPatrolRadius;
    float dist_leave_patrol = kDistLeavePatrol;
    float dist_leave_defend = kDistLeaveDefend;
    float dist_leave_attack = kDistLeaveAttack;
    float defend_time_sec = kDefendTimeSec;
    bool can_dodge_proj = true;
    float dist_start_dodge = kDistStartDodge;
    float dodge_cooldown_sec = kDodgeCooldownSec;
    bool predictive_targeting = kPredictiveTargeting;
    int predictive_targeting_chance = kPredictiveTargetingChance;
    float aiming_angle_deg = kAimingAngleDeg;
    bool perfect_aim = false;
    float safe_threshold = kSafeThresholdPx;
    float shoot_threshold = kShootThresholdPx;
    float mine_chance_per_sec = 0.0f;
    float mine_min_distance = 250.0f;
    bool random_mines = false;
};

ResolvedTuning ResolveTuning(const AIPersonalityTuning* tuning) {
    ResolvedTuning resolved;
    if (tuning != nullptr) {
        resolved.patrol_radius = tuning->patrol_radius;
        resolved.dist_leave_patrol = tuning->dist_leave_patrol;
        resolved.dist_leave_defend = tuning->dist_leave_defend;
        resolved.dist_leave_attack = tuning->dist_leave_attack;
        resolved.defend_time_sec = tuning->defend_time_sec;
        resolved.can_dodge_proj = tuning->can_dodge_proj;
        resolved.dist_start_dodge = tuning->dist_start_dodge;
        resolved.dodge_cooldown_sec = tuning->dodge_cooldown_sec;
        resolved.predictive_targeting = tuning->predictive_targeting;
        resolved.predictive_targeting_chance = tuning->predictive_targeting_chance;
        resolved.aiming_angle_deg = tuning->aiming_angle_deg;
        resolved.perfect_aim = tuning->perfect_aim;
        resolved.safe_threshold = tuning->safe_threshold;
        resolved.shoot_threshold = tuning->shoot_threshold;
        resolved.mine_chance_per_sec = tuning->mine_chance_per_sec;
        resolved.mine_min_distance = tuning->mine_min_distance;
        resolved.random_mines = tuning->random_mines;
    }
    return resolved;
}

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

void PickPatrolTarget(WorldQuery& world, const Transform& transform, const AIControlled& ai, NavAgent& nav_agent,
                       float patrol_radius) {
    const auto candidates = world.Navigation().FindValidNodesNear(ai.spawn_position, patrol_radius);
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

// True if `point` (a mine/self/ally) is close enough to any segment of `ray` to make firing
// unsafe - checked both against the ray's ordinary segments and, if present, a widened check
// around an ambiguous near-corner bounce point (see PredictedRay::ambiguous_corner).
bool IsUnsafeNear(const PredictedRay& ray, const Vec2& point, float threshold) {
    for (const auto& [seg_a, seg_b] : ray.segments) {
        if (IsPointNearSegment(seg_a, seg_b, point, threshold)) {
            return true;
        }
    }
    if (ray.ambiguous_corner && (*ray.ambiguous_corner - point).Length() < threshold) {
        return true;
    }
    return false;
}

// Direct-aim-with-lead targeting (M2b: intercept-lead solve when the target is moving, an
// aiming-inaccuracy cone re-rolled on a timer) plus the shoot-safety gate (ray-bounce shot
// prediction; refuses to fire if the predicted path passes too close to a live mine, self, or
// any other living unit besides the current target - matching the original, which is not
// team-based: it avoids hitting literally anyone else, not just allies).
void UpdateTargetingAndFiring(entt::registry& registry, WorldQuery& world, entt::entity entity, AIControlled& ai,
                               const ResolvedTuning& tuning, const Transform& transform, entt::entity target,
                               AimIntent& aim_intent, FireIntent& fire_intent, float dt) {
    if (target == entt::null) {
        return;
    }
    const auto& target_transform = registry.get<Transform>(target);

    // Intercept lead: chance-gated, only for a moving target (matches the original's
    // predictive_targeting/predictive_targeting_chance/is_moving gate; the original's
    // additional collision_timer<=0 gate has no analogue here since this port doesn't currently
    // track "just bounced off a wall" state on units, a minor simplification).
    Vec2 aim_point = target_transform.position;
    const auto* target_intent = registry.try_get<MovementIntent>(target);
    const auto* target_movement = registry.try_get<TrackedMovement>(target);
    if (target_intent != nullptr && target_movement != nullptr && target_intent->throttle != 0.0f) {
        const float rads = target_transform.heading_deg * kDegToRad;
        const Vec2 target_velocity =
            Vec2{std::cos(rads), std::sin(rads)} * (target_intent->throttle * target_movement->max_speed);

        std::uniform_int_distribution<int> chance_dist(0, 99);
        if (tuning.predictive_targeting && chance_dist(Rng()) < tuning.predictive_targeting_chance) {
            const auto* weapon_mounts = registry.try_get<WeaponMounts>(entity);
            const float projectile_speed = (weapon_mounts != nullptr && !weapon_mounts->weapons.empty())
                                                ? weapon_mounts->weapons[0].def.projectile_speed
                                                : kDefaultProjectileSpeed;
            aim_point = InterceptPoint(transform.position, projectile_speed, target_transform.position, target_velocity);
        }
    }

    // Aiming-inaccuracy cone, re-rolled on a timer (not every tick - see AIControlled::aim_jitter_deg).
    // Skipped entirely for a perfect_aim personality, matching the original.
    if (!tuning.perfect_aim) {
        ai.aim_jitter_timer_sec -= dt;
        if (ai.aim_jitter_timer_sec <= 0.0f) {
            std::uniform_real_distribution<float> jitter_dist(-tuning.aiming_angle_deg, tuning.aiming_angle_deg);
            ai.aim_jitter_deg = jitter_dist(Rng());
            ai.aim_jitter_timer_sec = kAimJitterReRollSec;
        }
        const Vec2 to_aim = aim_point - transform.position;
        const float aim_dist = to_aim.Length();
        if (aim_dist > 1.0f) {
            const float jittered_heading = std::atan2(to_aim.y, to_aim.x) * kRadToDeg + ai.aim_jitter_deg;
            const float rad = jittered_heading * kDegToRad;
            aim_point = transform.position + Vec2{std::cos(rad), std::sin(rad)} * aim_dist;
        }
    }
    aim_intent.target = aim_point;

    // Shoot-safety gate: predict the actual bounce path this shot would take, then only fire if
    // it's both safe (doesn't pass near a mine/self/any other unit) and on target.
    const Vec2 fire_direction = aim_point - transform.position;
    if (fire_direction.LengthSquared() < 1.0f) {
        return;
    }
    const auto* weapon_mounts = registry.try_get<WeaponMounts>(entity);
    const int bounce_limit =
        (weapon_mounts != nullptr && !weapon_mounts->weapons.empty()) ? weapon_mounts->weapons[0].def.bounce_limit : kDefaultBounceLimit;

    const Vec2 fire_direction_unit = fire_direction.Normalized();
    const Vec2 ray_start = transform.position + fire_direction_unit * kFireSpawnOffset;
    const PredictedRay predicted =
        PredictBouncePath(world.Obstacles(), ray_start, fire_direction_unit, std::max(0, bounce_limit - 1));

    bool can_shoot = true;
    for (auto mine_entity : registry.view<MineState, Transform>()) {
        const auto& mine = registry.get<MineState>(mine_entity);
        const auto& mine_transform = registry.get<Transform>(mine_entity);
        if ((mine_transform.position - transform.position).Length() < mine.explode_radius * 1.3f &&
            IsUnsafeNear(predicted, mine_transform.position, tuning.safe_threshold)) {
            can_shoot = false;
            break;
        }
    }
    if (can_shoot && IsUnsafeNear(predicted, transform.position, tuning.safe_threshold)) {
        can_shoot = false;  // Don't shoot ourselves via a ricochet.
    }
    if (can_shoot) {
        for (auto other : registry.view<Transform, Health>()) {
            if (other == entity || other == target) {
                continue;
            }
            if (registry.get<Health>(other).current <= 0.0f) {
                continue;
            }
            // Not team-based, matching the original: avoid hitting literally anyone else, not
            // just allies - the AI won't shoot through a bystander (of any team) to reach its
            // actual target.
            if (IsUnsafeNear(predicted, registry.get<Transform>(other).position, tuning.safe_threshold)) {
                can_shoot = false;
                break;
            }
        }
    }

    if (can_shoot) {
        for (const auto& [seg_a, seg_b] : predicted.segments) {
            if (IsPointNearSegment(seg_a, seg_b, target_transform.position, tuning.shoot_threshold)) {
                fire_intent.weapon_slot = 0;
                fire_intent.want_fire = true;
                break;
            }
        }
    }
}

// AI-driven mine laying (M3, previously unimplemented - only the player could lay mines):
// approximates the original's misc_updates() mine block. mine_chance_per_sec already folds in
// the original's "1-in-mine_chance per 60Hz AI tick" into an expected-rate-per-second so it's
// independent of this port's own tick rate; a random_mines personality lays regardless of
// target proximity, otherwise only when the target is within mine_min_distance.
void UpdateMineLaying(entt::registry& registry, entt::entity entity, const ResolvedTuning& tuning, entt::entity target,
                       const Transform& transform, MineIntent& mine_intent, float dt) {
    mine_intent.want_deploy = false;
    if (tuning.mine_chance_per_sec <= 0.0f) {
        return;
    }
    const auto* deployer = registry.try_get<MineDeployer>(entity);
    if (deployer == nullptr || deployer->limit <= 0) {
        return;
    }
    std::uniform_real_distribution<float> roll(0.0f, 1.0f);
    if (roll(Rng()) >= tuning.mine_chance_per_sec * dt) {
        return;
    }
    if (tuning.random_mines) {
        mine_intent.want_deploy = true;
        return;
    }
    if (target != entt::null && (registry.get<Transform>(target).position - transform.position).Length() <= tuning.mine_min_distance) {
        mine_intent.want_deploy = true;
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

        const ResolvedTuning tuning = ResolveTuning(registry.try_get<AIPersonalityTuning>(entity));

        // --- Targeting: intercept-lead aim, an inaccuracy cone, and the ray-bounce shoot-safety
        // gate (M2b). Runs unconditionally (even an immobile turret-only unit still aims/fires). ---
        const entt::entity target = FindNearestEnemy(registry, entity, faction.team, transform.position);
        ai.targeted_unit = target;
        UpdateTargetingAndFiring(registry, world, entity, ai, tuning, transform, target, aim_intent, fire_intent, dt);

        // Mine laying (M3): independent of movement/dodge below, so even a stationary
        // (max_speed<=0) turret-only unit can still lay mines, matching the original.
        if (auto* mine_intent = registry.try_get<MineIntent>(entity)) {
            UpdateMineLaying(registry, entity, tuning, target, transform, *mine_intent, dt);
        }

        const auto* movement = registry.try_get<TrackedMovement>(entity);
        if (movement == nullptr || movement->max_speed <= 0.0f) {
            continue;  // Immobile (turret-only) unit: aims/fires/lays mines above, never patrols/moves.
        }

        auto* nav_agent = registry.try_get<NavAgent>(entity);

        // --- Dodge: a global interrupt that can preempt any other state, matching the original. ---
        if (ai.dodge_cooldown_sec > 0.0f) {
            ai.dodge_cooldown_sec -= dt;
        }
        if (tuning.can_dodge_proj && ai.state != BehaviorState::Dodge && ai.dodge_cooldown_sec <= 0.0f) {
            if (const auto threat = FindNearestProjectileThreat(registry, transform.position, tuning.dist_start_dodge)) {
                ai.state = BehaviorState::Dodge;
                ClearPath(nav_agent);
                if (nav_agent != nullptr) {
                    PickDodgeTarget(world, transform, *threat, *nav_agent);
                }
                ai.dodge_cooldown_sec = tuning.dodge_cooldown_sec;
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
                    PickPatrolTarget(world, transform, ai, *nav_agent, tuning.patrol_radius);
                }
                if (target != entt::null &&
                    (registry.get<Transform>(target).position - transform.position).Length() < tuning.dist_leave_patrol) {
                    ai.state = BehaviorState::Defending;
                    ai.state_timer_sec = 0.0f;
                    ClearPath(nav_agent);
                }
                break;

            case BehaviorState::Defending: {
                if (ai.state_timer_sec <= 0.0f) {
                    ai.state_timer_sec = tuning.defend_time_sec;
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
                if ((target_pos - transform.position).Length() > tuning.dist_leave_defend) {
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
                if ((target_pos - transform.position).Length() < tuning.dist_leave_attack) {
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
