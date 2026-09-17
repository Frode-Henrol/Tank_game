#include "tank/sim/mine_system.hpp"

#include <vector>

#include "tank/ecs/gameplay_components.hpp"

namespace tank::sim {

using tank::ecs::Faction;
using tank::ecs::Health;
using tank::ecs::MineDeployer;
using tank::ecs::MineIntent;
using tank::ecs::MineState;
using tank::ecs::Transform;
using tank::ecs::Vec2;

namespace {
// Configured mine stats. Hardcoded for M1 (no data-driven unit defs yet - that lands in M3,
// when this becomes a per-UnitDef MineDef instead).
constexpr float kMineCooldownSec = 1.0f;
constexpr float kMineExplodeRadius = 100.0f;
constexpr float kMineLifeTimerSec = 10.0f;
constexpr float kMineCountdownSec = 2.0f;
constexpr float kMineCleanupDelaySec = 0.5f;
}  // namespace

void MineSystem::Update(entt::registry& registry, physics::ObstacleWorld& world, float dt) {
    // --- Deploy new mines ---
    auto deployer_view = registry.view<Transform, MineDeployer, MineIntent, Faction>();
    for (auto entity : deployer_view) {
        const auto& transform = deployer_view.get<Transform>(entity);
        auto& deployer = deployer_view.get<MineDeployer>(entity);
        const auto& intent = deployer_view.get<MineIntent>(entity);
        const auto& faction = deployer_view.get<Faction>(entity);

        if (deployer.cooldown_sec > 0.0f) {
            deployer.cooldown_sec -= dt;
        }

        if (!intent.want_deploy || deployer.cooldown_sec > 0.0f || deployer.active_count >= deployer.limit) {
            continue;
        }

        const auto mine_entity = registry.create();
        registry.emplace<Transform>(mine_entity, transform.position, 0.0f);
        registry.emplace<MineState>(mine_entity, MineState{entity, faction.team, kMineExplodeRadius, kMineLifeTimerSec,
                                                              kMineCountdownSec, false, false, kMineCleanupDelaySec});
        deployer.cooldown_sec = kMineCooldownSec;
        ++deployer.active_count;
    }

    // --- Tick existing mines ---
    std::vector<entt::entity> to_destroy;
    auto mine_view = registry.view<Transform, MineState>();
    auto tank_view = registry.view<Transform, Faction, Health>();

    for (auto entity : mine_view) {
        const auto& transform = mine_view.get<Transform>(entity);
        auto& mine = mine_view.get<MineState>(entity);

        if (mine.exploded) {
            mine.cleanup_delay_sec -= dt;
            if (mine.cleanup_delay_sec <= 0.0f) {
                to_destroy.push_back(entity);
                if (registry.valid(mine.owner) && registry.all_of<MineDeployer>(mine.owner)) {
                    --registry.get<MineDeployer>(mine.owner).active_count;
                }
            }
            continue;
        }

        if (!mine.countdown_started) {
            mine.life_timer_sec -= dt;
            if (mine.life_timer_sec <= 0.0f) {
                mine.countdown_started = true;
            }
        }

        for (auto tank_entity : tank_view) {
            const auto& tank_faction = tank_view.get<Faction>(tank_entity);
            const auto& tank_health = tank_view.get<Health>(tank_entity);
            if (tank_faction.team == mine.team || tank_health.current <= 0.0f) {
                continue;
            }
            const auto& tank_transform = tank_view.get<Transform>(tank_entity);
            if ((tank_transform.position - transform.position).LengthSquared() < mine.explode_radius * mine.explode_radius) {
                if (!mine.countdown_started) {
                    mine.countdown_timer_sec *= 0.25f;
                }
                mine.countdown_started = true;
            }
        }

        if (!mine.countdown_started) {
            continue;
        }

        mine.countdown_timer_sec -= dt;
        if (mine.countdown_timer_sec > 0.0f) {
            continue;
        }

        // --- Explode ---
        for (auto tank_entity : tank_view) {
            auto& tank_health = tank_view.get<Health>(tank_entity);
            if (tank_health.current <= 0.0f) {
                continue;
            }
            const auto& tank_transform = tank_view.get<Transform>(tank_entity);
            if ((tank_transform.position - transform.position).LengthSquared() < mine.explode_radius * mine.explode_radius) {
                tank_health.current -= tank_health.max;
            }
        }

        auto& obstacles = world.MutableObstacles();
        for (std::size_t i = 0; i < obstacles.size(); ++i) {
            if (obstacles[i].destroyed || obstacles[i].type != physics::ObstacleType::Destructible) {
                continue;
            }
            for (const Vec2& corner : obstacles[i].polygon) {
                if ((corner - transform.position).LengthSquared() < mine.explode_radius * mine.explode_radius) {
                    world.DestroyObstacle(i);
                    break;
                }
            }
        }

        mine.exploded = true;
    }

    for (auto entity : to_destroy) {
        registry.destroy(entity);
    }
}

}  // namespace tank::sim
