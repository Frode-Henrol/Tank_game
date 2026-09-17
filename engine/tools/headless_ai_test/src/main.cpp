// Acceptance test for "AI completely decoupled from unit classes": this binary links only
// tank::ai + tank::physics + tank::ecs (+ entt transitively) - notably NOT SDL3, and no concrete
// unit/vehicle type. That this links and runs at all is part of the proof; the fixtures below
// are the M2a acceptance gate proper - they exercise the real behavior FSM and pathfinding
// against fixture data and assert on state transitions and fire decisions, not just "it didn't
// crash."

#include <cassert>
#include <cstdio>
#include <string>

#include <entt/entt.hpp>

#include "tank/ai/behavior_system.hpp"
#include "tank/ai/nav_grid.hpp"
#include "tank/ai/world_query.hpp"
#include "tank/ecs/gameplay_components.hpp"

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

    behavior_system.Update(registry, world, dt);

    const auto& fire = registry.get<ecs::FireIntent>(unit);
    const auto& aim = registry.get<ecs::AimIntent>(unit);
    Check(fire.want_fire, "a unit with a living enemy in range wants to fire");
    Check(aim.target.x == registry.get<ecs::Transform>(enemy).position.x &&
              aim.target.y == registry.get<ecs::Transform>(enemy).position.y,
          "aim target is the enemy's exact current position (M2a: no lead/prediction yet)");

    registry.get<ecs::Health>(enemy).current = 0.0f;  // Kill the only enemy.
    behavior_system.Update(registry, world, dt);
    Check(!registry.get<ecs::FireIntent>(unit).want_fire, "no living enemy left means no fire intent");
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

}  // namespace

int main() {
    TestIdleToPatrol();
    TestPatrolToDefendToAttack();
    TestTargetingAndFiring();
    TestDodge();

    if (g_failures == 0) {
        std::printf("\nheadless_ai_test: ALL CHECKS PASSED (ai module builds/runs with zero SDL linked)\n");
        return 0;
    }
    std::printf("\nheadless_ai_test: %d CHECK(S) FAILED\n", g_failures);
    return 1;
}
