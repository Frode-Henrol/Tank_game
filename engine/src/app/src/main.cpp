// M0 smoke test: boots a window, runs the fixed-timestep loop through the full (non-multiplayer)
// State graph, and proves the ecs/sim/render pieces connect end to end by letting the player
// drive one real sprite (reused directly from the existing Python project's assets) around the
// screen while in the Playing state. Tab cycles through every state to confirm the single game
// loop drives all of them (no blocking per-state sub-loops); Escape quits.

#include <algorithm>
#include <array>
#include <cstdio>
#include <string>

#include <SDL3/SDL.h>
#include <entt/entt.hpp>

#include "tank/core/app.hpp"
#include "tank/core/state.hpp"
#include "tank/ecs/gameplay_components.hpp"
#include "tank/render/sprite_renderer.hpp"
#include "tank/render/texture_cache.hpp"
#include "tank/render/window.hpp"
#include "tank/sim/movement_system.hpp"

namespace {

constexpr std::array<tank::core::State, 14> kAllStates{
    tank::core::State::Menu,          tank::core::State::SettingsMain, tank::core::State::SettingsDebug,
    tank::core::State::SettingsControls, tank::core::State::PauseMenu, tank::core::State::LoadoutSelect,
    tank::core::State::LevelSelect,   tank::core::State::ControlScreen, tank::core::State::Countdown,
    tank::core::State::Playing,       tank::core::State::Playthrough,  tank::core::State::InfoScreen,
    tank::core::State::EndScreen,     tank::core::State::Exit,
};

const char* StateName(tank::core::State state) {
    switch (state) {
        case tank::core::State::Menu:
            return "Menu";
        case tank::core::State::SettingsMain:
            return "SettingsMain";
        case tank::core::State::SettingsDebug:
            return "SettingsDebug";
        case tank::core::State::SettingsControls:
            return "SettingsControls";
        case tank::core::State::PauseMenu:
            return "PauseMenu";
        case tank::core::State::LoadoutSelect:
            return "LoadoutSelect";
        case tank::core::State::LevelSelect:
            return "LevelSelect";
        case tank::core::State::ControlScreen:
            return "ControlScreen";
        case tank::core::State::Countdown:
            return "Countdown";
        case tank::core::State::Playing:
            return "Playing";
        case tank::core::State::Playthrough:
            return "Playthrough";
        case tank::core::State::InfoScreen:
            return "InfoScreen";
        case tank::core::State::EndScreen:
            return "EndScreen";
        case tank::core::State::Exit:
            return "Exit";
    }
    return "?";
}

// A distinct clear color per state, purely so cycling states (Tab) is visually confirmable
// without any UI having been built yet (that's M4's job).
void ClearForState(tank::render::Window& window, tank::core::State state) {
    const auto index = static_cast<std::size_t>(
        std::find(kAllStates.begin(), kAllStates.end(), state) - kAllStates.begin());
    const float hue = static_cast<float>(index) / static_cast<float>(kAllStates.size());
    window.Clear(0.15f + 0.5f * hue, 0.15f, 0.35f - 0.2f * hue);
}

}  // namespace

int main(int /*argc*/, char** /*argv*/) {
    tank::render::Window window("Tank Game (engine skeleton - M0)", 1280, 720);
    tank::render::TextureCache textures(window.Renderer());

    entt::registry registry;

    const auto demo_tank = registry.create();
    registry.emplace<tank::ecs::Transform>(demo_tank, tank::ecs::Vec2{640.0f, 360.0f}, 0.0f);
    registry.emplace<tank::ecs::TrackedMovement>(demo_tank, 200.0f, 180.0f);
    registry.emplace<tank::ecs::MovementIntent>(demo_tank);
    registry.emplace<tank::ecs::Sprite>(
        demo_tank, tank::ecs::Sprite{std::string(ASSET_ROOT) + "/units/images/player1_tank.png", 0.5f, 0.5f, 64.0f,
                                      64.0f, 90.0f});

    tank::sim::TrackedMovementSystem movement_system;

    tank::core::App app(window, 1.0f / 100.0f);

    std::size_t state_index = 0;
    app.SetKeyDownCallback([&](int scancode) {
        if (scancode == SDL_SCANCODE_TAB) {
            state_index = (state_index + 1) % kAllStates.size();
            app.SetState(kAllStates[state_index]);
            std::printf("State -> %s\n", StateName(app.CurrentState()));
        }
    });

    app.SetUpdateCallback([&](tank::core::State state, float dt) {
        if (state != tank::core::State::Playing) {
            return;
        }

        const bool* keys = SDL_GetKeyboardState(nullptr);
        auto& intent = registry.get<tank::ecs::MovementIntent>(demo_tank);
        intent.throttle = static_cast<float>(keys[SDL_SCANCODE_W]) - static_cast<float>(keys[SDL_SCANCODE_S]);
        intent.turn_axis = static_cast<float>(keys[SDL_SCANCODE_D]) - static_cast<float>(keys[SDL_SCANCODE_A]);

        movement_system.Update(registry, dt);
    });

    app.SetRenderCallback([&](tank::core::State state) {
        ClearForState(window, state);
        if (state == tank::core::State::Playing) {
            auto view = registry.view<tank::ecs::Transform, tank::ecs::Sprite>();
            for (auto entity : view) {
                tank::render::DrawSprite(window.Renderer(), textures, view.get<tank::ecs::Transform>(entity),
                                          view.get<tank::ecs::Sprite>(entity));
            }
        }
    });

    std::printf("Tab: cycle state | WASD: drive (while Playing) | Escape: quit\n");
    std::printf("State -> %s\n", StateName(app.CurrentState()));

    app.Run();
    return 0;
}
