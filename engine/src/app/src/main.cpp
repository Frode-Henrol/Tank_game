// M1 smoke test: loads a real map (tankgame/map_files/map_test1.txt, parsed by the original's
// unmodified text format), builds the physics::ObstacleWorld from it, spawns every unit the map
// defines as an ECS entity (team 1 = the player, driven by WASD/mouse/E; everything else sits
// idle, since AI is still a stub until M2), and runs the full M1 system pipeline every fixed
// tick: movement, wall collision + push-back, tank-tank repulsion, weapon firing, projectile
// movement/bounce/damage, and mine deploy/arm/explode. 'N' spawns a wave of synthetic stress
// entities to sanity-check scaling; the printed average tick time is the scalability signal.
//
// Tab still cycles every non-Playing state (menus etc. are still just stub-colored screens -
// full UI lands in M4); Escape quits.

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <optional>
#include <random>
#include <string>
#include <vector>

#include <SDL3/SDL.h>
#include <entt/entt.hpp>

#include "tank/ai/behavior_system.hpp"
#include "tank/ai/world_query.hpp"
#include "tank/content/map_loader.hpp"
#include "tank/core/app.hpp"
#include "tank/core/state.hpp"
#include "tank/ecs/gameplay_components.hpp"
#include "tank/physics/obstacle_world.hpp"
#include "tank/physics/oriented_box.hpp"
#include "tank/render/polygon_renderer.hpp"
#include "tank/render/sprite_renderer.hpp"
#include "tank/render/texture_cache.hpp"
#include "tank/render/window.hpp"
#include "tank/sim/collision_system.hpp"
#include "tank/sim/mine_system.hpp"
#include "tank/sim/movement_system.hpp"
#include "tank/sim/projectile_system.hpp"
#include "tank/sim/weapon_system.hpp"

namespace ecs = tank::ecs;
using tank::ecs::Vec2;

namespace {

constexpr std::array<tank::core::State, 14> kAllStates{
    tank::core::State::Menu,          tank::core::State::SettingsMain,  tank::core::State::SettingsDebug,
    tank::core::State::SettingsControls, tank::core::State::PauseMenu,  tank::core::State::LoadoutSelect,
    tank::core::State::LevelSelect,   tank::core::State::ControlScreen, tank::core::State::Countdown,
    tank::core::State::Playing,       tank::core::State::Playthrough,  tank::core::State::InfoScreen,
    tank::core::State::EndScreen,     tank::core::State::Exit,
};

void ClearForState(tank::render::Window& window, tank::core::State state) {
    const auto index =
        static_cast<std::size_t>(std::find(kAllStates.begin(), kAllStates.end(), state) - kAllStates.begin());
    const float hue = static_cast<float>(index) / static_cast<float>(kAllStates.size());
    window.Clear(0.1f + 0.3f * hue, 0.12f, 0.2f - 0.1f * hue);
}

// ai::WorldQuery is deliberately minimal until M2's behavior FSM needs concrete queries.
struct NullWorldQuery : tank::ai::WorldQuery {};

entt::entity SpawnTank(entt::registry& registry, const tank::content::UnitSpawn& spawn,
                       tank::render::TextureCache& textures, const std::string& asset_root) {
    (void)textures;  // Texture is lazily loaded by TextureCache::Get() the first time it's drawn.
    const auto entity = registry.create();

    registry.emplace<ecs::Transform>(entity, spawn.position, spawn.angle_deg);
    registry.emplace<ecs::TrackedMovement>(entity, 115.2f, 180.0f);
    registry.emplace<ecs::CollisionShape>(entity, ecs::ColliderShape::Box, 20.0f, 20.0f);
    registry.emplace<ecs::Health>(entity, 1.0f, 1.0f, 1.0f);
    registry.emplace<ecs::Faction>(entity, spawn.team);
    registry.emplace<ecs::MovementIntent>(entity);
    registry.emplace<ecs::AimIntent>(entity, Vec2{spawn.position.x + 1.0f, spawn.position.y});
    registry.emplace<ecs::FireIntent>(entity);
    registry.emplace<ecs::MineIntent>(entity);
    registry.emplace<ecs::MineDeployer>(entity, 0.0f, 4, 0);

    ecs::WeaponDef def{};
    def.fire_interval_sec = 2.0f * 5.0f / 60.0f;  // matches player_classic's firerate=2 normalization
    def.projectile_speed = 3.36f * 60.0f;         // matches player_classic's projectile_speed_modifier
    def.bounce_limit = 2;
    def.projectile_limit = 5;
    def.damage = 1.0f;
    registry.emplace<ecs::WeaponMounts>(entity, ecs::WeaponMounts{{ecs::WeaponState{def, 0.0f, 0, 0.0f, false}}});

    const bool is_player = spawn.team == 1;
    const std::string texture = asset_root + (is_player ? "/units/images/player1_tank.png" : "/units/images/violet_tank.png");
    registry.emplace<ecs::Sprite>(entity, ecs::Sprite{texture, 0.5f, 0.5f, 40.0f, 48.0f, 90.0f});

    if (is_player) {
        registry.emplace<ecs::PlayerControlled>(entity, 0);
    } else {
        registry.emplace<ecs::AIControlled>(entity);
    }
    return entity;
}

void SpawnStressEntities(entt::registry& registry, const tank::content::MapData& map, int count) {
    static std::mt19937 rng{std::random_device{}()};
    if (map.border.size() < 4) {
        return;
    }
    float min_x = map.border[0].x, max_x = map.border[0].x;
    float min_y = map.border[0].y, max_y = map.border[0].y;
    for (const Vec2& corner : map.border) {
        min_x = std::min(min_x, corner.x);
        max_x = std::max(max_x, corner.x);
        min_y = std::min(min_y, corner.y);
        max_y = std::max(max_y, corner.y);
    }
    std::uniform_real_distribution<float> dist_x(min_x + 30.0f, max_x - 30.0f);
    std::uniform_real_distribution<float> dist_y(min_y + 30.0f, max_y - 30.0f);

    for (int i = 0; i < count; ++i) {
        const auto entity = registry.create();
        registry.emplace<ecs::Transform>(entity, Vec2{dist_x(rng), dist_y(rng)}, 0.0f);
        registry.emplace<ecs::TrackedMovement>(entity, 0.0f, 0.0f);
        registry.emplace<ecs::CollisionShape>(entity, ecs::ColliderShape::Box, 20.0f, 20.0f);
        registry.emplace<ecs::Health>(entity, 1.0f, 1.0f, 1.0f);
        registry.emplace<ecs::Faction>(entity, 99);
        registry.emplace<ecs::MovementIntent>(entity);
    }
}

}  // namespace

int main(int /*argc*/, char** /*argv*/) {
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    const std::string asset_root = ASSET_ROOT;
    const auto map = tank::content::LoadMap(asset_root + "/map_files/map_test1.txt");
    if (!map) {
        std::fprintf(stderr, "Failed to load map - aborting.\n");
        return 1;
    }

    tank::render::Window window("Tank Game (engine skeleton - M1)", 1400, 950);
    tank::render::TextureCache textures(window.Renderer());

    tank::physics::ObstacleWorld obstacle_world;
    obstacle_world.SetObstacles(map->obstacles);
    const tank::physics::OrientedBoxCache box_cache;

    entt::registry registry;
    entt::entity player_entity = entt::null;
    for (const auto& spawn : map->spawns) {
        const auto entity = SpawnTank(registry, spawn, textures, asset_root);
        if (spawn.team == 1) {
            player_entity = entity;
        }
    }

    tank::sim::TrackedMovementSystem movement_system;
    tank::sim::WallCollisionSystem wall_collision_system(box_cache);
    tank::sim::TankRepulsionSystem repulsion_system;
    tank::sim::WeaponSystem weapon_system;
    tank::sim::ProjectileSystem projectile_system;
    tank::sim::MineSystem mine_system;
    tank::ai::BehaviorSystem behavior_system;
    NullWorldQuery world_query;

    tank::core::App app(window, 1.0f / 100.0f);

    std::size_t state_index = 9;  // Start straight in Playing for the M1 smoke test.
    app.SetState(tank::core::State::Playing);

    double tick_time_accum_ms = 0.0;
    int tick_count = 0;

    app.SetKeyDownCallback([&](int scancode) {
        if (scancode == SDL_SCANCODE_TAB) {
            state_index = (state_index + 1) % kAllStates.size();
            app.SetState(kAllStates[state_index]);
        } else if (scancode == SDL_SCANCODE_N) {
            SpawnStressEntities(registry, *map, 200);
            std::printf("Spawned 200 stress entities (total entities: %zu)\n",
                        static_cast<std::size_t>(registry.storage<entt::entity>().size()));
        } else if (scancode == SDL_SCANCODE_P) {
            std::printf("--- entity dump ---\n");
            for (auto entity : registry.view<ecs::Transform, ecs::Faction, ecs::Health>()) {
                const auto& t = registry.get<ecs::Transform>(entity);
                const auto& f = registry.get<ecs::Faction>(entity);
                const auto& h = registry.get<ecs::Health>(entity);
                std::printf("  entity=%u team=%d pos=(%.1f,%.1f) heading=%.1f hp=%.1f\n",
                            static_cast<unsigned>(entity), f.team, t.position.x, t.position.y, t.heading_deg, h.current);
            }
            std::printf("projectiles alive: %zu, mines alive: %zu\n",
                        static_cast<std::size_t>(registry.view<ecs::ProjectileState>().size()),
                        static_cast<std::size_t>(registry.view<ecs::MineState>().size()));
            if (registry.valid(player_entity)) {
                const auto& fire = registry.get<ecs::FireIntent>(player_entity);
                const auto& mine_intent = registry.get<ecs::MineIntent>(player_entity);
                const auto& aim = registry.get<ecs::AimIntent>(player_entity);
                std::printf("player want_fire=%d want_deploy=%d aim=(%.1f,%.1f)\n", fire.want_fire, mine_intent.want_deploy,
                            aim.target.x, aim.target.y);
            }
            for (auto entity : registry.view<ecs::ProjectileState>()) {
                const auto& p = registry.get<ecs::ProjectileState>(entity);
                const auto& t = registry.get<ecs::Transform>(entity);
                std::printf("  projectile owner=%u pos=(%.1f,%.1f) dir=(%.2f,%.2f) bounce=%d/%d\n",
                            static_cast<unsigned>(p.owner), t.position.x, t.position.y, p.direction.x, p.direction.y,
                            p.bounce_count, p.bounce_limit);
            }
        }
    });

    app.SetUpdateCallback([&](tank::core::State state, float dt) {
        if (state != tank::core::State::Playing) {
            return;
        }

        const auto tick_start = SDL_GetPerformanceCounter();

        if (registry.valid(player_entity)) {
            const bool* keys = SDL_GetKeyboardState(nullptr);
            auto& intent = registry.get<ecs::MovementIntent>(player_entity);
            intent.throttle = static_cast<float>(keys[SDL_SCANCODE_W]) - static_cast<float>(keys[SDL_SCANCODE_S]);
            intent.turn_axis = static_cast<float>(keys[SDL_SCANCODE_D]) - static_cast<float>(keys[SDL_SCANCODE_A]);

            float mouse_x = 0.0f;
            float mouse_y = 0.0f;
            const auto buttons = SDL_GetMouseState(&mouse_x, &mouse_y);
            registry.get<ecs::AimIntent>(player_entity).target = Vec2{mouse_x, mouse_y};
            registry.get<ecs::FireIntent>(player_entity).want_fire = (buttons & SDL_BUTTON_LMASK) != 0;
            registry.get<ecs::MineIntent>(player_entity).want_deploy = keys[SDL_SCANCODE_E];
        }

        behavior_system.Update(registry, world_query, dt);
        movement_system.Update(registry, dt);
        wall_collision_system.Update(registry, obstacle_world, dt);
        repulsion_system.Update(registry, dt);
        weapon_system.Update(registry, dt);
        projectile_system.Update(registry, obstacle_world, box_cache, dt);
        mine_system.Update(registry, obstacle_world, dt);

        const auto tick_end = SDL_GetPerformanceCounter();
        const double tick_ms =
            static_cast<double>(tick_end - tick_start) * 1000.0 / static_cast<double>(SDL_GetPerformanceFrequency());
        tick_time_accum_ms += tick_ms;
        ++tick_count;
        if (tick_count >= 200) {
            std::printf("Avg tick time over last %d ticks: %.3f ms (entities: %zu, projectiles: %zu, mines: %zu)\n",
                        tick_count, tick_time_accum_ms / tick_count,
                        static_cast<std::size_t>(registry.storage<entt::entity>().size()),
                        static_cast<std::size_t>(registry.view<ecs::ProjectileState>().size()),
                        static_cast<std::size_t>(registry.view<ecs::MineState>().size()));
            if (registry.valid(player_entity)) {
                const auto& fire = registry.get<ecs::FireIntent>(player_entity);
                const auto& mine_intent = registry.get<ecs::MineIntent>(player_entity);
                const auto& aim = registry.get<ecs::AimIntent>(player_entity);
                const auto& ptransform = registry.get<ecs::Transform>(player_entity);
                std::printf("  player pos=(%.1f,%.1f) want_fire=%d want_deploy=%d aim=(%.1f,%.1f)\n", ptransform.position.x,
                            ptransform.position.y, fire.want_fire, mine_intent.want_deploy, aim.target.x, aim.target.y);
            }
            for (auto entity : registry.view<ecs::Faction, ecs::Health>()) {
                const auto& h = registry.get<ecs::Health>(entity);
                if (h.current <= 0.0f) {
                    std::printf("  DEAD entity=%u\n", static_cast<unsigned>(entity));
                }
            }
            tick_time_accum_ms = 0.0;
            tick_count = 0;
        }
    });

    app.SetRenderCallback([&](tank::core::State state) {
        ClearForState(window, state);
        if (state != tank::core::State::Playing) {
            return;
        }

        for (const auto& obstacle : obstacle_world.Obstacles()) {
            if (obstacle.destroyed) {
                continue;
            }
            tank::render::Color color{0.5f, 0.5f, 0.5f, 1.0f};
            if (obstacle.type == tank::physics::ObstacleType::Destructible) {
                color = {0.55f, 0.35f, 0.2f, 1.0f};
            } else if (obstacle.type == tank::physics::ObstacleType::Pit) {
                color = {0.05f, 0.05f, 0.05f, 1.0f};
            }
            tank::render::DrawFilledPolygon(window.Renderer(), obstacle.polygon, color);
        }

        for (auto entity : registry.view<ecs::Transform, ecs::MineState>()) {
            const auto& transform = registry.get<ecs::Transform>(entity);
            const auto& mine = registry.get<ecs::MineState>(entity);
            const tank::render::Color color = mine.exploded ? tank::render::Color{0.9f, 0.1f, 0.1f, 1.0f}
                                                              : tank::render::Color{0.9f, 0.85f, 0.1f, 1.0f};
            std::vector<Vec2> octagon;
            for (int i = 0; i < 8; ++i) {
                const float angle = static_cast<float>(i) * (3.14159265f / 4.0f);
                octagon.push_back(Vec2{transform.position.x + 8.0f * std::cos(angle),
                                        transform.position.y + 8.0f * std::sin(angle)});
            }
            tank::render::DrawFilledPolygon(window.Renderer(), octagon, color);
        }

        for (auto entity : registry.view<ecs::Transform, ecs::Health, ecs::Sprite>()) {
            // A dead tank stops rendering (no body/turret sprite - a death-marker sprite is a
            // content/rendering detail for a later milestone) but its collision box stays live,
            // see collision_system.cpp / projectile_system.cpp: the wreck still physically
            // blocks/absorbs shots and pushes/blocks other tanks even though it's invisible.
            if (registry.get<ecs::Health>(entity).current <= 0.0f) {
                continue;
            }
            tank::render::DrawSprite(window.Renderer(), textures, registry.get<ecs::Transform>(entity),
                                      registry.get<ecs::Sprite>(entity));
        }

        SDL_SetRenderDrawColorFloat(window.Renderer(), 1.0f, 0.6f, 0.1f, 1.0f);
        for (auto entity : registry.view<ecs::Transform, ecs::ProjectileState>()) {
            const auto& transform = registry.get<ecs::Transform>(entity);
            const auto& projectile = registry.get<ecs::ProjectileState>(entity);
            const Vec2 tip = transform.position + projectile.direction * 10.0f;
            SDL_RenderLine(window.Renderer(), transform.position.x, transform.position.y, tip.x, tip.y);
        }
    });

    std::printf("Tab: cycle state | WASD: drive | mouse: aim | LMB: fire | E: lay mine | N: stress test | Escape: quit\n");
    app.Run();
    return 0;
}
