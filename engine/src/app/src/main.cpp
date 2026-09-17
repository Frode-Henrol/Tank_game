// The real game flow (M4): Menu -> LoadoutSelect -> ControlScreen -> (Playthrough init) ->
// InfoScreen -> Countdown -> Playing -> (level-end settle) -> Playthrough referee -> InfoScreen
// or EndScreen, with PauseMenu reachable from Playing via Escape and a Settings sub-graph off
// both Menu and PauseMenu. Lives/level-number progression and the map file pattern
// (map_files/lvl{N}.txt) mirror the original tankgame.py; loadout/level-select UI is
// deliberately simplified (a numeric stepper instead of porting the original's free-text
// Textfield widget - "UI logic ... can be changed if there are better ways of doing it").
//
// Every state, including timed ones (Countdown/InfoScreen/EndScreen), is ticked from the one
// fixed-timestep loop in tank::core::App - no blocking sub-loops with their own clocks like the
// original had. Settings screens are intentionally minimal this pass (context-aware Back button
// only, no real toggles yet); animations (shake/flash/fade) and audio are deferred to a later
// continuation per the project plan.

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <functional>
#include <optional>
#include <random>
#include <set>
#include <string>
#include <vector>

#include <SDL3/SDL.h>
#include <entt/entt.hpp>

#include "tank/ai/behavior_system.hpp"
#include "tank/ai/nav_grid.hpp"
#include "tank/ai/world_query.hpp"
#include "tank/content/map_loader.hpp"
#include "tank/content/unit_def.hpp"
#include "tank/content/unit_factory.hpp"
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
#include "tank/ui/button.hpp"
#include "tank/ui/font.hpp"

namespace ecs = tank::ecs;
using tank::ecs::Vec2;

namespace {

// A pragmatic Windows-specific font path - documented as needing a bundled/portable font before
// this ever ships cross-platform.
constexpr const char* kFontPath = "C:/Windows/Fonts/arial.ttf";

constexpr int kStartingLives = 3;
constexpr int kLastLevel = 50;
constexpr int kNewLifeInterval = 5;
constexpr float kPostRoundWaitSec = 3.0f;   // settle time after a death/clear before the referee runs
constexpr float kInfoScreenNormalSec = 4.0f;
constexpr float kInfoScreenGameOverSec = 7.0f;
constexpr float kEndScreenSec = 8.0f;
constexpr float kCountdownStepSec = 1.0f;

struct ButtonSpec {
    std::string text;
    std::optional<tank::core::State> target;
    std::function<void()> action;
};

// Ties the AI module's read-only view of the level to this app's actual obstacle world / nav
// grid, which the ai module itself never constructs (it only ever sees them through this
// interface - see tank/ai/world_query.hpp).
class GameWorldQuery : public tank::ai::WorldQuery {
public:
    GameWorldQuery(const tank::physics::ObstacleWorld& obstacles, const tank::ai::NavGrid& nav_grid)
        : obstacles_(obstacles), nav_grid_(nav_grid) {}

    [[nodiscard]] const tank::physics::ObstacleWorld& Obstacles() const override { return obstacles_; }
    [[nodiscard]] const tank::ai::NavGrid& Navigation() const override { return nav_grid_; }

private:
    const tank::physics::ObstacleWorld& obstacles_;
    const tank::ai::NavGrid& nav_grid_;
};

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

// Owns the whole game: session/campaign state, the live level (registry + level geometry), the
// system pipeline, and the UI (fonts/buttons) for every screen. One instance, constructed once
// in main().
class GameApp {
public:
    GameApp(tank::render::Window& window, std::string asset_root);

    void Run() { app_.Run(); }

private:
    struct Session {
        bool playthrough_started = false;
        int current_level_number = 1;
        int lives = kStartingLives;
        std::string selected_loadout = "player_classic";
        std::set<int> levels_that_gave_life;
        bool just_died = false;
        bool added_life = false;
        int level_select_value = 1;
    };

    void OnKeyDown(int scancode);
    void OnMouseDown(float x, float y, int button);
    void Update(tank::core::State state, float dt);
    void Render(tank::core::State state);

    void UpdatePlaying(float dt);
    void DumpEntityState();

    // Changes app_'s state, rebuilds that screen's buttons, and runs any one-shot per-state
    // entry side effects (session reset on returning to Menu, timer resets, etc). The only
    // place SetState is ever called from - keeps "which state resets what" in one spot.
    void TransitionTo(tank::core::State state);
    void BuildButtonsForState(tank::core::State state);
    void LayoutVerticalButtons(const std::vector<ButtonSpec>& specs, float center_x, float top_y);

    void BeginPlaythroughAndLoadLevel();
    void LoadLevel(int level_number);
    void RunPlaythroughReferee();

    void DrawWorld();
    void DrawButtons();
    void DrawCenteredText(tank::ui::Font& font, const std::string& text, float center_x, float center_y,
                           SDL_Color tint);

    tank::render::Window& window_;
    std::string asset_root_;
    tank::render::TextureCache textures_;
    tank::ui::Font font_ui_;
    tank::ui::Font font_headline_;
    tank::core::App app_;

    tank::content::UnitDefTable unit_defs_;
    tank::content::AIPersonalityTable ai_personalities_;

    entt::registry registry_;
    entt::entity player_entity_ = entt::null;
    std::optional<tank::content::MapData> current_map_;
    tank::physics::ObstacleWorld obstacle_world_;
    tank::physics::OrientedBoxCache box_cache_;
    std::optional<tank::ai::NavGrid> nav_grid_;
    std::optional<GameWorldQuery> world_query_;

    tank::sim::TrackedMovementSystem movement_system_;
    tank::sim::WallCollisionSystem wall_collision_system_;
    tank::sim::TankRepulsionSystem repulsion_system_;
    tank::sim::WeaponSystem weapon_system_;
    tank::sim::ProjectileSystem projectile_system_;
    tank::sim::MineSystem mine_system_;
    tank::ai::BehaviorSystem behavior_system_;

    Session session_;
    std::vector<tank::ui::Button> buttons_;

    float countdown_timer_ = 0.0f;
    int countdown_number_ = 3;
    float info_screen_timer_ = 0.0f;
    float end_screen_timer_ = 0.0f;
    float playthrough_wait_timer_ = 0.0f;

    double tick_time_accum_ms_ = 0.0;
    int tick_count_ = 0;
};

GameApp::GameApp(tank::render::Window& window, std::string asset_root)
    : window_(window),
      asset_root_(std::move(asset_root)),
      textures_(window.Renderer()),
      font_ui_(kFontPath, 26.0f),
      font_headline_(kFontPath, 72.0f),
      app_(window, 1.0f / 100.0f),
      unit_defs_(tank::content::LoadUnitDefs(asset_root_ + "/units/units.json")),
      ai_personalities_(tank::content::LoadAIPersonalities(asset_root_ + "/units/ai.json")),
      wall_collision_system_(box_cache_) {
    app_.SetKeyDownCallback([this](int scancode) { OnKeyDown(scancode); });
    app_.SetMouseDownCallback([this](float x, float y, int button) { OnMouseDown(x, y, button); });
    app_.SetUpdateCallback([this](tank::core::State state, float dt) { Update(state, dt); });
    app_.SetRenderCallback([this](tank::core::State state) { Render(state); });
    TransitionTo(tank::core::State::Menu);
}

void GameApp::TransitionTo(tank::core::State state) {
    if (state == tank::core::State::Menu && session_.playthrough_started) {
        session_ = Session{};
    }
    if (state == tank::core::State::LevelSelect) {
        session_.level_select_value = session_.current_level_number;
    }
    if (state == tank::core::State::Countdown) {
        countdown_timer_ = 0.0f;
        countdown_number_ = 3;
    }
    if (state == tank::core::State::InfoScreen) {
        info_screen_timer_ = 0.0f;
    }
    if (state == tank::core::State::EndScreen) {
        end_screen_timer_ = 0.0f;
    }
    if (state == tank::core::State::Exit) {
        app_.RequestQuit();
    }
    app_.SetState(state);
    BuildButtonsForState(state);
}

void GameApp::LayoutVerticalButtons(const std::vector<ButtonSpec>& specs, float center_x, float top_y) {
    constexpr float kWidth = 320.0f;
    constexpr float kHeight = 60.0f;
    constexpr float kSpacing = 18.0f;
    float y = top_y;
    for (const auto& spec : specs) {
        tank::ui::Button button;
        button.x = center_x - kWidth / 2.0f;
        button.y = y;
        button.width = kWidth;
        button.height = kHeight;
        button.text = spec.text;
        button.target_state = spec.target;
        button.action = spec.action;
        buttons_.push_back(std::move(button));
        y += kHeight + kSpacing;
    }
}

void GameApp::BuildButtonsForState(tank::core::State state) {
    buttons_.clear();
    const float center_x = static_cast<float>(window_.Width()) / 2.0f;

    switch (state) {
        case tank::core::State::Menu:
            LayoutVerticalButtons(
                {
                    {"Start Game", tank::core::State::LoadoutSelect, {}},
                    {"Level Select", tank::core::State::LevelSelect, {}},
                    {"Settings", tank::core::State::SettingsMain, {}},
                    {"Quit Game", tank::core::State::Exit, {}},
                },
                center_x, 300.0f);
            break;

        case tank::core::State::LoadoutSelect:
            LayoutVerticalButtons(
                {
                    {"Classic", tank::core::State::ControlScreen, [this] { session_.selected_loadout = "player_classic"; }},
                    {"Sniper", tank::core::State::ControlScreen, [this] { session_.selected_loadout = "player_sniper"; }},
                    {"Autocannon", tank::core::State::ControlScreen,
                     [this] { session_.selected_loadout = "player_autocannon"; }},
                    {"Bouncer", tank::core::State::ControlScreen, [this] { session_.selected_loadout = "player_bouncer"; }},
                    {"Burst", tank::core::State::ControlScreen, [this] { session_.selected_loadout = "player_burst"; }},
                    {"Back", tank::core::State::Menu, {}},
                },
                center_x, 140.0f);
            break;

        case tank::core::State::LevelSelect: {
            constexpr float kStepW = 90.0f;
            constexpr float kStepH = 60.0f;
            constexpr float kGap = 16.0f;
            float x = center_x - (kStepW * 4.0f + kGap * 3.0f) / 2.0f;
            const float y = 420.0f;
            auto add_step = [&](const std::string& text, std::function<void()> action) {
                tank::ui::Button button;
                button.x = x;
                button.y = y;
                button.width = kStepW;
                button.height = kStepH;
                button.text = text;
                button.action = std::move(action);
                buttons_.push_back(std::move(button));
                x += kStepW + kGap;
            };
            add_step("-10", [this] { session_.level_select_value = std::max(1, session_.level_select_value - 10); });
            add_step("-1", [this] { session_.level_select_value = std::max(1, session_.level_select_value - 1); });
            add_step("+1", [this] { session_.level_select_value = std::min(kLastLevel, session_.level_select_value + 1); });
            add_step("+10",
                      [this] { session_.level_select_value = std::min(kLastLevel, session_.level_select_value + 10); });
            LayoutVerticalButtons(
                {
                    {"Play", tank::core::State::LoadoutSelect,
                     [this] { session_.current_level_number = session_.level_select_value; }},
                    {"Back", tank::core::State::Menu, {}},
                },
                center_x, 540.0f);
            break;
        }

        case tank::core::State::ControlScreen:
            LayoutVerticalButtons(
                {
                    {"Start", tank::core::State::InfoScreen, [this] { BeginPlaythroughAndLoadLevel(); }},
                },
                center_x, 800.0f);
            break;

        case tank::core::State::PauseMenu:
            LayoutVerticalButtons(
                {
                    {"Resume", tank::core::State::Playing, {}},
                    {"Settings", tank::core::State::SettingsMain, {}},
                    {"Main Menu", tank::core::State::Menu, {}},
                },
                center_x, 350.0f);
            break;

        case tank::core::State::SettingsMain: {
            const auto back_target =
                session_.playthrough_started ? tank::core::State::PauseMenu : tank::core::State::Menu;
            LayoutVerticalButtons(
                {
                    {"Debug", tank::core::State::SettingsDebug, {}},
                    {"Controls", tank::core::State::SettingsControls, {}},
                    {"Back", back_target, {}},
                },
                center_x, 350.0f);
            break;
        }

        case tank::core::State::SettingsDebug:
        case tank::core::State::SettingsControls:
            LayoutVerticalButtons(
                {
                    {"Back", tank::core::State::SettingsMain, {}},
                },
                center_x, 700.0f);
            break;

        default:
            break;  // Countdown/Playing/Playthrough/InfoScreen/EndScreen/Exit have no buttons.
    }
}

void GameApp::BeginPlaythroughAndLoadLevel() {
    session_.playthrough_started = true;
    session_.lives = kStartingLives;
    session_.levels_that_gave_life.clear();
    session_.just_died = false;
    session_.added_life = false;
    LoadLevel(session_.current_level_number);
}

void GameApp::LoadLevel(int level_number) {
    const std::string path = asset_root_ + "/map_files/lvl" + std::to_string(level_number) + ".txt";
    auto map = tank::content::LoadMap(path);
    if (!map) {
        std::fprintf(stderr, "Failed to load level %d ('%s').\n", level_number, path.c_str());
        return;
    }
    current_map_ = std::move(map);
    obstacle_world_.SetObstacles(current_map_->obstacles);
    // border is [bottom-left, bottom-right, top-right, top-left] per the original map format.
    nav_grid_.emplace(current_map_->border[3], current_map_->border[1],
                       static_cast<float>(current_map_->node_spacing), obstacle_world_.Obstacles());
    world_query_.emplace(obstacle_world_, *nav_grid_);

    registry_.clear();
    player_entity_ = entt::null;
    for (const auto& spawn : current_map_->spawns) {
        const tank::content::SpawnParams params{spawn.position, spawn.angle_deg, spawn.team, spawn.type_code};
        const auto entity = tank::content::SpawnUnit(registry_, unit_defs_, ai_personalities_, params, asset_root_,
                                                        session_.selected_loadout);
        if (spawn.team == 1) {
            player_entity_ = entity;
        }
    }
    playthrough_wait_timer_ = 0.0f;
}

void GameApp::RunPlaythroughReferee() {
    const bool player_alive =
        registry_.valid(player_entity_) && registry_.get<ecs::Health>(player_entity_).current > 0.0f;

    if (!player_alive) {
        session_.lives -= 1;
        session_.just_died = true;
        session_.added_life = false;
        LoadLevel(session_.current_level_number);
        TransitionTo(tank::core::State::InfoScreen);
        return;
    }

    session_.just_died = false;
    if (session_.current_level_number % kNewLifeInterval == 0 &&
        !session_.levels_that_gave_life.count(session_.current_level_number)) {
        session_.lives += 1;
        session_.added_life = true;
        session_.levels_that_gave_life.insert(session_.current_level_number);
    } else {
        session_.added_life = false;
    }

    session_.current_level_number += 1;
    if (session_.current_level_number > kLastLevel) {
        TransitionTo(tank::core::State::EndScreen);
        return;
    }
    LoadLevel(session_.current_level_number);
    TransitionTo(tank::core::State::InfoScreen);
}

void GameApp::OnKeyDown(int scancode) {
    const auto state = app_.CurrentState();
    if (state == tank::core::State::Playing) {
        if (scancode == SDL_SCANCODE_ESCAPE) {
            TransitionTo(tank::core::State::PauseMenu);
        } else if (scancode == SDL_SCANCODE_N) {
            if (current_map_) {
                SpawnStressEntities(registry_, *current_map_, 200);
                std::printf("Spawned 200 stress entities (total entities: %zu)\n",
                            static_cast<std::size_t>(registry_.storage<entt::entity>().free_list()));
            }
        } else if (scancode == SDL_SCANCODE_P) {
            DumpEntityState();
        }
    } else if (state == tank::core::State::ControlScreen && scancode == SDL_SCANCODE_RETURN) {
        BeginPlaythroughAndLoadLevel();
        TransitionTo(tank::core::State::InfoScreen);
    }
}

void GameApp::OnMouseDown(float x, float y, int button) {
    if (button != SDL_BUTTON_LEFT) {
        return;
    }
    for (std::size_t i = 0; i < buttons_.size(); ++i) {
        if (!buttons_[i].Contains(x, y)) {
            continue;
        }
        const auto target = tank::ui::HandleMouseDown(buttons_[i], x, y);
        if (target) {
            TransitionTo(*target);
        }
        break;  // buttons_ may have just been rebuilt by TransitionTo - stop touching it.
    }
}

void GameApp::Update(tank::core::State state, float dt) {
    if (!buttons_.empty()) {
        float mouse_x = 0.0f, mouse_y = 0.0f;
        SDL_GetMouseState(&mouse_x, &mouse_y);
        for (auto& button : buttons_) {
            tank::ui::HandleMouseMotion(button, mouse_x, mouse_y);
        }
    }

    switch (state) {
        case tank::core::State::Countdown:
            countdown_timer_ += dt;
            if (countdown_timer_ >= kCountdownStepSec) {
                countdown_timer_ -= kCountdownStepSec;
                --countdown_number_;
                if (countdown_number_ <= 0) {
                    TransitionTo(tank::core::State::Playing);
                }
            }
            break;

        case tank::core::State::InfoScreen: {
            info_screen_timer_ += dt;
            const bool game_over = session_.lives <= 0;
            const float duration = game_over ? kInfoScreenGameOverSec : kInfoScreenNormalSec;
            if (info_screen_timer_ >= duration) {
                session_.just_died = false;
                session_.added_life = false;
                TransitionTo(game_over ? tank::core::State::Menu : tank::core::State::Countdown);
            }
            break;
        }

        case tank::core::State::EndScreen:
            end_screen_timer_ += dt;
            if (end_screen_timer_ >= kEndScreenSec) {
                TransitionTo(tank::core::State::Menu);
            }
            break;

        case tank::core::State::Playthrough:
            RunPlaythroughReferee();
            break;

        case tank::core::State::Playing:
            UpdatePlaying(dt);
            break;

        default:
            break;
    }
}

void GameApp::UpdatePlaying(float dt) {
    const auto tick_start = SDL_GetPerformanceCounter();

    if (registry_.valid(player_entity_)) {
        const bool* keys = SDL_GetKeyboardState(nullptr);
        auto& intent = registry_.get<ecs::MovementIntent>(player_entity_);
        intent.throttle = static_cast<float>(keys[SDL_SCANCODE_W]) - static_cast<float>(keys[SDL_SCANCODE_S]);
        intent.turn_axis = static_cast<float>(keys[SDL_SCANCODE_D]) - static_cast<float>(keys[SDL_SCANCODE_A]);

        float mouse_x = 0.0f, mouse_y = 0.0f;
        const auto mouse_buttons = SDL_GetMouseState(&mouse_x, &mouse_y);
        registry_.get<ecs::AimIntent>(player_entity_).target = Vec2{mouse_x, mouse_y};
        registry_.get<ecs::FireIntent>(player_entity_).want_fire = (mouse_buttons & SDL_BUTTON_LMASK) != 0;
        registry_.get<ecs::MineIntent>(player_entity_).want_deploy = keys[SDL_SCANCODE_E];
    }

    if (world_query_) {
        behavior_system_.Update(registry_, *world_query_, dt);
    }
    movement_system_.Update(registry_, dt);
    wall_collision_system_.Update(registry_, obstacle_world_, dt);
    repulsion_system_.Update(registry_, dt);
    weapon_system_.Update(registry_, dt);
    projectile_system_.Update(registry_, obstacle_world_, dt);
    mine_system_.Update(registry_, obstacle_world_, dt);

    // Level-end detection: hold the settled result for kPostRoundWaitSec (matching the
    // original's 3s grace window) before handing off to the Playthrough referee, so a death/
    // clear isn't judged mid-explosion.
    const bool player_alive =
        registry_.valid(player_entity_) && registry_.get<ecs::Health>(player_entity_).current > 0.0f;
    bool all_enemies_dead = false;
    if (player_alive) {
        const int player_team = registry_.get<ecs::Faction>(player_entity_).team;
        all_enemies_dead = true;
        for (auto entity : registry_.view<ecs::Faction, ecs::Health>()) {
            const auto& faction = registry_.get<ecs::Faction>(entity);
            if (faction.team == player_team) {
                continue;
            }
            if (registry_.get<ecs::Health>(entity).current > 0.0f) {
                all_enemies_dead = false;
                break;
            }
        }
    }

    if (!player_alive || all_enemies_dead) {
        playthrough_wait_timer_ += dt;
        if (playthrough_wait_timer_ >= kPostRoundWaitSec) {
            playthrough_wait_timer_ = 0.0f;
            TransitionTo(tank::core::State::Playthrough);
        }
    } else {
        playthrough_wait_timer_ = 0.0f;
    }

    const auto tick_end = SDL_GetPerformanceCounter();
    tick_time_accum_ms_ +=
        static_cast<double>(tick_end - tick_start) * 1000.0 / static_cast<double>(SDL_GetPerformanceFrequency());
    ++tick_count_;
    if (tick_count_ >= 200) {
        std::printf("Avg tick time over last %d ticks: %.3f ms (entities: %zu, projectiles: %zu, mines: %zu)\n",
                     tick_count_, tick_time_accum_ms_ / tick_count_,
                     static_cast<std::size_t>(registry_.storage<entt::entity>().free_list()),
                     static_cast<std::size_t>(registry_.view<ecs::ProjectileState>().size()),
                     static_cast<std::size_t>(registry_.view<ecs::MineState>().size()));
        tick_time_accum_ms_ = 0.0;
        tick_count_ = 0;
    }
}

void GameApp::DumpEntityState() {
    std::printf("--- entity dump (level %d, lives %d) ---\n", session_.current_level_number, session_.lives);
    for (auto entity : registry_.view<ecs::Transform, ecs::Faction, ecs::Health>()) {
        const auto& transform = registry_.get<ecs::Transform>(entity);
        const auto& faction = registry_.get<ecs::Faction>(entity);
        const auto& health = registry_.get<ecs::Health>(entity);
        std::printf("  entity=%u team=%d pos=(%.1f,%.1f) heading=%.1f hp=%.1f\n", static_cast<unsigned>(entity),
                    faction.team, transform.position.x, transform.position.y, transform.heading_deg, health.current);
    }
    std::printf("projectiles alive: %zu, mines alive: %zu\n",
                static_cast<std::size_t>(registry_.view<ecs::ProjectileState>().size()),
                static_cast<std::size_t>(registry_.view<ecs::MineState>().size()));
}

void GameApp::DrawWorld() {
    for (const auto& obstacle : obstacle_world_.Obstacles()) {
        if (obstacle.destroyed) {
            continue;
        }
        tank::render::Color color{0.5f, 0.5f, 0.5f, 1.0f};
        if (obstacle.type == tank::physics::ObstacleType::Destructible) {
            color = {0.55f, 0.35f, 0.2f, 1.0f};
        } else if (obstacle.type == tank::physics::ObstacleType::Pit) {
            color = {0.05f, 0.05f, 0.05f, 1.0f};
        }
        tank::render::DrawFilledPolygon(window_.Renderer(), obstacle.polygon, color);
    }

    for (auto entity : registry_.view<ecs::Transform, ecs::MineState>()) {
        const auto& transform = registry_.get<ecs::Transform>(entity);
        const auto& mine = registry_.get<ecs::MineState>(entity);
        const tank::render::Color color = mine.exploded ? tank::render::Color{0.9f, 0.1f, 0.1f, 1.0f}
                                                          : tank::render::Color{0.9f, 0.85f, 0.1f, 1.0f};
        std::vector<Vec2> octagon;
        for (int i = 0; i < 8; ++i) {
            const float angle = static_cast<float>(i) * (3.14159265f / 4.0f);
            octagon.push_back(
                Vec2{transform.position.x + 8.0f * std::cos(angle), transform.position.y + 8.0f * std::sin(angle)});
        }
        tank::render::DrawFilledPolygon(window_.Renderer(), octagon, color);
    }

    for (auto entity : registry_.view<ecs::Transform, ecs::Health, ecs::Sprite>()) {
        // A dead tank stops rendering (body/turret sprite) but its collision box stays live -
        // see collision_system.cpp/projectile_system.cpp: the wreck still physically blocks/
        // absorbs shots and pushes/blocks other tanks even though it's invisible.
        if (registry_.get<ecs::Health>(entity).current <= 0.0f) {
            continue;
        }
        tank::render::DrawSprite(window_.Renderer(), textures_, registry_.get<ecs::Transform>(entity),
                                  registry_.get<ecs::Sprite>(entity));
    }

    SDL_SetRenderDrawColorFloat(window_.Renderer(), 1.0f, 0.6f, 0.1f, 1.0f);
    for (auto entity : registry_.view<ecs::Transform, ecs::ProjectileState>()) {
        const auto& transform = registry_.get<ecs::Transform>(entity);
        const auto& projectile = registry_.get<ecs::ProjectileState>(entity);
        const Vec2 tip = transform.position + projectile.direction * 10.0f;
        SDL_RenderLine(window_.Renderer(), transform.position.x, transform.position.y, tip.x, tip.y);
    }
}

void GameApp::DrawButtons() {
    for (const auto& button : buttons_) {
        tank::ui::DrawButton(window_.Renderer(), font_ui_, button);
    }
}

void GameApp::DrawCenteredText(tank::ui::Font& font, const std::string& text, float center_x, float center_y,
                                SDL_Color tint) {
    if (text.empty()) {
        return;
    }
    SDL_Texture* texture = font.GetTextTexture(window_.Renderer(), text);
    if (texture == nullptr) {
        return;
    }
    SDL_SetTextureColorMod(texture, tint.r, tint.g, tint.b);
    float width = 0.0f, height = 0.0f;
    SDL_GetTextureSize(texture, &width, &height);
    const SDL_FRect dst{center_x - width / 2.0f, center_y - height / 2.0f, width, height};
    SDL_RenderTexture(window_.Renderer(), texture, nullptr, &dst);
}

void GameApp::Render(tank::core::State state) {
    const float center_x = static_cast<float>(window_.Width()) / 2.0f;
    const float height = static_cast<float>(window_.Height());

    if (state == tank::core::State::Playing || state == tank::core::State::Countdown ||
        state == tank::core::State::PauseMenu) {
        window_.Clear(0.08f, 0.09f, 0.11f);
        DrawWorld();
    } else {
        window_.Clear(0.12f, 0.11f, 0.16f);
    }

    switch (state) {
        case tank::core::State::Countdown:
            if (countdown_number_ > 0) {
                DrawCenteredText(font_headline_, std::to_string(countdown_number_), center_x, height / 2.0f,
                                  {255, 255, 255, 255});
            }
            break;

        case tank::core::State::InfoScreen: {
            SDL_Color tint{255, 220, 80, 255};
            if (session_.just_died) {
                tint = SDL_Color{220, 60, 60, 255};
            } else if (session_.added_life) {
                tint = SDL_Color{80, 220, 120, 255};
            }
            DrawCenteredText(font_headline_, "Level " + std::to_string(session_.current_level_number), center_x,
                              height * 0.35f, tint);
            DrawCenteredText(font_ui_, "Lives: " + std::to_string(std::max(0, session_.lives)), center_x,
                              height * 0.5f, tint);
            if (session_.lives <= 0) {
                DrawCenteredText(font_headline_, "GAME OVER", center_x, height * 0.65f, SDL_Color{220, 40, 40, 255});
            }
            break;
        }

        case tank::core::State::EndScreen:
            DrawCenteredText(font_headline_, "YOU WON!", center_x, height / 2.0f, {255, 255, 255, 255});
            break;

        case tank::core::State::LevelSelect:
            DrawCenteredText(font_headline_, "Level: " + std::to_string(session_.level_select_value), center_x,
                              340.0f, {255, 255, 255, 255});
            break;

        case tank::core::State::ControlScreen:
            DrawCenteredText(font_ui_, "WASD move | Mouse aim | LMB fire | E lay mine", center_x, height * 0.28f,
                              {255, 255, 255, 255});
            DrawCenteredText(font_ui_, "Press Enter or click Start", center_x, height * 0.36f, {200, 200, 200, 255});
            break;

        case tank::core::State::SettingsDebug:
            DrawCenteredText(font_ui_, "Debug keys during Playing: N = spawn stress entities, P = dump entity state",
                              center_x, height * 0.3f, {255, 255, 255, 255});
            break;

        case tank::core::State::SettingsControls:
            DrawCenteredText(font_ui_, "Control remapping: coming soon", center_x, height * 0.3f, {255, 255, 255, 255});
            break;

        default:
            break;
    }

    DrawButtons();
}

}  // namespace

int main(int /*argc*/, char** /*argv*/) {
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    const std::string asset_root = ASSET_ROOT;

    tank::render::Window window("Tank Game", 1400, 950);
    GameApp game(window, asset_root);

    std::printf("Tank Game running - use the menu to start a campaign.\n");
    game.Run();
    return 0;
}
