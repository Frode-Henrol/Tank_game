// Acceptance test for "AI completely decoupled from unit classes": this binary links only
// tank::ai + tank::physics + tank::ecs (+ entt transitively) - notably NOT SDL3, and no concrete
// unit/vehicle type. That this links and runs at all is part of the proof; the fixtures below
// are the M2a acceptance gate proper - they exercise the real behavior FSM and pathfinding
// against fixture data and assert on state transitions and fire decisions, not just "it didn't
// crash."

#include <cassert>
#include <cmath>
#include <cstdio>
#include <string>

#include <entt/entt.hpp>

#include "tank/ai/behavior_system.hpp"
#include "tank/ai/nav_grid.hpp"
#include "tank/ai/targeting.hpp"
#include "tank/ai/world_query.hpp"
#include "tank/ecs/gameplay_components.hpp"
#include "tank/sim/projectile_system.hpp"

namespace ecs = tank::ecs;
using tank::ecs::Vec2;

namespace {

int g_failures = 0;

void Check(bool condition, const std::string& description) {
    if (condition) {
        std::printf("  [PASS] %s\n", description.c_str());
    } else {
        std::printf("  [FAIL] %s\n", description.c_str());
        ++g_failures;
    }
}

// A concrete WorldQuery over a synthetic open field (no obstacles) - enough to exercise the
// behavior FSM and pathfinding without needing a real map file (which would pull in
// tank::content, unnecessarily widening what this decoupling-proof binary links).
class FixtureWorldQuery : public tank::ai::WorldQuery {
public:
    FixtureWorldQuery()
        : obstacles_(150.0f), nav_grid_(Vec2{0.0f, 0.0f}, Vec2{2000.0f, 2000.0f}, 50.0f, obstacles_.Obstacles()) {}

    [[nodiscard]] const tank::physics::ObstacleWorld& Obstacles() const override { return obstacles_; }
    [[nodiscard]] const tank::ai::NavGrid& Navigation() const override { return nav_grid_; }

private:
    tank::physics::ObstacleWorld obstacles_;
    tank::ai::NavGrid nav_grid_;
};

entt::entity SpawnAIUnit(entt::registry& registry, const Vec2& pos, int team) {
    const auto entity = registry.create();
    registry.emplace<ecs::Transform>(entity, pos, 0.0f);
    registry.emplace<ecs::TrackedMovement>(entity, 100.0f, 90.0f);
    registry.emplace<ecs::Faction>(entity, team);
    registry.emplace<ecs::Health>(entity, 1.0f, 1.0f, 1.0f);
    registry.emplace<ecs::AIControlled>(entity);
    registry.emplace<ecs::NavAgent>(entity);
    registry.emplace<ecs::MovementIntent>(entity);
    registry.emplace<ecs::AimIntent>(entity);
    registry.emplace<ecs::FireIntent>(entity);
    return entity;
}

void TestIdleToPatrol() {
    std::printf("-- IdleToPatrol --\n");
    entt::registry registry;
    FixtureWorldQuery world;
    tank::ai::BehaviorSystem behavior_system;
    constexpr float dt = 1.0f / 100.0f;

    const auto unit = SpawnAIUnit(registry, Vec2{1000.0f, 1000.0f}, 1);  // No enemies anywhere.

    behavior_system.Update(registry, world, dt);
    Check(registry.get<ecs::AIControlled>(unit).state == ecs::BehaviorState::Patrolling,
          "an idle unit with no enemies transitions to Patrolling on its first update");

    bool got_a_path = false;
    for (int i = 0; i < 20 && !got_a_path; ++i) {
        behavior_system.Update(registry, world, dt);
        if (!registry.get<ecs::NavAgent>(unit).path.empty()) {
            got_a_path = true;
        }
    }
    Check(got_a_path, "a patrolling unit picks a real path from the nav grid");
}

void TestPatrolToDefendToAttack() {
    std::printf("-- PatrolToDefendToAttack --\n");
    entt::registry registry;
    FixtureWorldQuery world;
    tank::ai::BehaviorSystem behavior_system;
    constexpr float dt = 1.0f / 100.0f;

    const auto unit = SpawnAIUnit(registry, Vec2{1000.0f, 1000.0f}, 1);
    SpawnAIUnit(registry, Vec2{1100.0f, 1000.0f}, 2);  // Enemy 100px away - well inside dist_leave_patrol.

    behavior_system.Update(registry, world, dt);
    Check(registry.get<ecs::AIControlled>(unit).state == ecs::BehaviorState::Defending,
          "an enemy within range sends a freshly-idle unit straight to Defending (via one Patrolling tick)");

    bool reached_attacking = false;
    for (int i = 0; i < 700 && !reached_attacking; ++i) {  // defend_time is a few seconds at 100Hz
        behavior_system.Update(registry, world, dt);
        if (registry.get<ecs::AIControlled>(unit).state == ecs::BehaviorState::Attacking) {
            reached_attacking = true;
        }
    }
    Check(reached_attacking, "Defending transitions to Attacking once its timer expires");
}

void TestTargetingAndFiring() {
    std::printf("-- TargetingAndFiring --\n");
    entt::registry registry;
    FixtureWorldQuery world;
    tank::ai::BehaviorSystem behavior_system;
    constexpr float dt = 1.0f / 100.0f;

    const auto unit = SpawnAIUnit(registry, Vec2{500.0f, 500.0f}, 1);
    const auto enemy = SpawnAIUnit(registry, Vec2{700.0f, 500.0f}, 2);
    const float enemy_dist = (registry.get<ecs::Transform>(enemy).position - Vec2{500.0f, 500.0f}).Length();

    // M2b adds an aiming-inaccuracy cone (re-rolled every ~1.5s, not every tick) and a
    // shoot-safety gate, so a single tick's fire decision is no longer guaranteed like it was
    // in M2a - run across several re-roll periods and require firing at least once, and check
    // the aim point stays *close to* (not exactly on) the enemy, consistent with the cone.
    bool ever_fired = false;
    float max_aim_deviation = 0.0f;
    for (int i = 0; i < 500; ++i) {
        behavior_system.Update(registry, world, dt);
        if (registry.get<ecs::FireIntent>(unit).want_fire) {
            ever_fired = true;
        }
        const auto& aim = registry.get<ecs::AimIntent>(unit);
        const float deviation = (aim.target - registry.get<ecs::Transform>(enemy).position).Length();
        max_aim_deviation = std::max(max_aim_deviation, deviation);
    }
    Check(ever_fired, "a unit with a living enemy in range fires at least once over several aim-jitter re-rolls");
    // A +/-15deg cone at ~200px range subtends at most ~200*tan(15deg) =~ 54px of lateral
    // deviation - stay well clear of that as a generous upper bound, confirming the aim is still
    // meaningfully "at the enemy" and not wildly off (e.g. not accidentally aiming at nothing).
    Check(max_aim_deviation < enemy_dist * 0.5f,
          "aim point stays close to the enemy (within the inaccuracy cone), never wildly off (max_deviation=" +
              std::to_string(max_aim_deviation) + ")");

    registry.get<ecs::Health>(enemy).current = 0.0f;  // Kill the only enemy.
    behavior_system.Update(registry, world, dt);
    Check(!registry.get<ecs::FireIntent>(unit).want_fire, "no living enemy left means no fire intent");
}

void TestShootSafetyGate() {
    std::printf("-- ShootSafetyGate --\n");
    // The original's safety check isn't team-based: it refuses to fire if the shot would pass
    // close to literally any other living unit besides the current target, not just allies.
    // FindNearestEnemy targets whichever enemy is closest (600,500 here); a second enemy sits
    // directly behind it on the same line (700,500) - since nothing here bounces the ray, it
    // continues straight past the target and would clip that second unit too, which should
    // block the shot even though it's the same team as the actual target, not an ally.
    entt::registry registry;
    FixtureWorldQuery world;
    tank::ai::BehaviorSystem behavior_system;
    constexpr float dt = 1.0f / 100.0f;

    const auto unit = SpawnAIUnit(registry, Vec2{500.0f, 500.0f}, 1);
    SpawnAIUnit(registry, Vec2{600.0f, 500.0f}, 2);  // nearest enemy - becomes the actual target
    SpawnAIUnit(registry, Vec2{700.0f, 500.0f}, 2);  // directly behind it on the same firing line

    bool ever_fired = false;
    for (int i = 0; i < 500; ++i) {
        behavior_system.Update(registry, world, dt);
        if (registry.get<ecs::FireIntent>(unit).want_fire) {
            ever_fired = true;
        }
    }
    Check(!ever_fired, "never fires when another living unit (any team) sits in the shot's path past the target");
}

void TestDodge() {
    std::printf("-- Dodge --\n");
    entt::registry registry;
    FixtureWorldQuery world;
    tank::ai::BehaviorSystem behavior_system;
    constexpr float dt = 1.0f / 100.0f;

    const auto unit = SpawnAIUnit(registry, Vec2{1000.0f, 1000.0f}, 1);

    const auto threat = registry.create();
    registry.emplace<ecs::Transform>(threat, Vec2{1030.0f, 1000.0f}, 0.0f);  // 30px away, well inside dodge range
    registry.emplace<ecs::ProjectileState>(
        threat, ecs::ProjectileState{entt::null, Vec2{-1.0f, 0.0f}, Vec2{1200.0f, 1000.0f}, 300.0f, 0, 1, 1.0f, 5.0f, 0.0f});

    behavior_system.Update(registry, world, dt);
    Check(registry.get<ecs::AIControlled>(unit).state == ecs::BehaviorState::Dodge,
          "an incoming projectile within dodge range preempts whatever state the unit was in");
}

void TestInterceptPoint() {
    std::printf("-- InterceptPoint --\n");
    // Shooter at the origin, projectile speed 100. Target starts 200px directly ahead (on the
    // x-axis) and moves straight along +y at 50/s - a simple case with a known closed-form
    // answer, worked by hand: intercept time t solves |target_pos + v*t| = speed*t, i.e.
    // (200)^2 + (50t)^2 = (100t)^2 => 40000 = 7500t^2 => t = sqrt(40000/7500) =~ 2.3094s,
    // landing at (200, 50*2.3094) =~ (200, 115.47).
    const Vec2 shooter{0.0f, 0.0f};
    const Vec2 target_pos{200.0f, 0.0f};
    const Vec2 target_velocity{0.0f, 50.0f};
    const Vec2 lead = tank::ai::InterceptPoint(shooter, 100.0f, target_pos, target_velocity);

    Check(std::fabs(lead.x - 200.0f) < 0.5f && std::fabs(lead.y - 115.47f) < 0.5f,
          "intercept point matches the closed-form hand-worked answer (got (" + std::to_string(lead.x) + "," +
              std::to_string(lead.y) + "), expected ~(200, 115.47))");

    // A stationary target needs no lead at all.
    const Vec2 no_lead = tank::ai::InterceptPoint(shooter, 100.0f, target_pos, Vec2{0.0f, 0.0f});
    Check(no_lead.x == target_pos.x && no_lead.y == target_pos.y, "a stationary target gets no lead correction");

    // A target outrunning the projectile (straight away, faster than it closes) has no real
    // solution - must fall back to the target's current position, not produce garbage.
    const Vec2 outrunning = tank::ai::InterceptPoint(shooter, 50.0f, target_pos, Vec2{100.0f, 0.0f});
    Check(outrunning.x == target_pos.x && outrunning.y == target_pos.y,
          "a target outrunning the projectile falls back to its current position, not a bogus lead");
}

void TestPredictedRayMatchesActualBounce() {
    std::printf("-- PredictedRayMatchesActualBounce --\n");
    // The plan's explicit verification approach for M2b: compare the AI's ray-bounce shot
    // *prediction* against ProjectileSystem's real, simulated bounce for the exact same start
    // position/direction/speed - if these two ever quietly diverge, AI accuracy silently
    // degrades (the original bug class this milestone exists to avoid).
    tank::physics::ObstacleWorld world;
    tank::physics::Obstacle wall{{{300.0f, 0.0f}, {310.0f, 0.0f}, {310.0f, 500.0f}, {300.0f, 500.0f}},
                                  tank::physics::ObstacleType::Standard,
                                  false};
    world.SetObstacles({wall});

    const Vec2 start{250.0f, 250.0f};
    const Vec2 direction{1.0f, 0.0f};
    constexpr float speed = 300.0f;
    constexpr float dt = 1.0f / 100.0f;

    const tank::ai::PredictedRay predicted = tank::ai::PredictBouncePath(world, start, direction, /*max_bounces=*/1);
    Check(predicted.segments.size() >= 1, "prediction produces at least one segment");
    const Vec2 predicted_bounce_point = predicted.segments.empty() ? Vec2{} : predicted.segments.front().second;

    entt::registry registry;
    const auto projectile = registry.create();
    registry.emplace<ecs::Transform>(projectile, start, 0.0f);
    registry.emplace<ecs::ProjectileState>(projectile,
                                            ecs::ProjectileState{entt::null, direction, start, speed, 0, 2, 1.0f, 5.0f, 0.0f});

    tank::sim::ProjectileSystem projectile_system;
    Vec2 actual_bounce_point{};
    bool actually_bounced = false;
    for (int i = 0; i < 50 && !actually_bounced; ++i) {
        projectile_system.Update(registry, world, dt);
        if (registry.get<ecs::ProjectileState>(projectile).bounce_count > 0) {
            actually_bounced = true;
            // Real position is nudged 0.1 units past the exact intersection along the new
            // (reflected) direction - undo that to compare against the exact hit point.
            const auto& state = registry.get<ecs::ProjectileState>(projectile);
            const auto& transform = registry.get<ecs::Transform>(projectile);
            actual_bounce_point = transform.position - state.direction * 0.1f;
        }
    }
    Check(actually_bounced, "the real projectile actually bounces off the same wall within a reasonable number of ticks");

    const float error = (predicted_bounce_point - actual_bounce_point).Length();
    Check(error < 1.0f,
          "predicted bounce point matches the real simulated one within 1px (predicted=(" +
              std::to_string(predicted_bounce_point.x) + "," + std::to_string(predicted_bounce_point.y) + "), actual=(" +
              std::to_string(actual_bounce_point.x) + "," + std::to_string(actual_bounce_point.y) +
              "), error=" + std::to_string(error) + ")");
}

}  // namespace

int main() {
    TestIdleToPatrol();
    TestPatrolToDefendToAttack();
    TestTargetingAndFiring();
    TestShootSafetyGate();
    TestDodge();
    TestInterceptPoint();
    TestPredictedRayMatchesActualBounce();

    if (g_failures == 0) {
        std::printf("\nheadless_ai_test: ALL CHECKS PASSED (ai module builds/runs with zero SDL linked)\n");
        return 0;
    }
    std::printf("\nheadless_ai_test: %d CHECK(S) FAILED\n", g_failures);
    return 1;
}
