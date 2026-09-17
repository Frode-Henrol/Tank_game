#pragma once

namespace tank::core {

// Full game state graph, minus everything multiplayer-only (dropped per the project scope).
enum class State {
    Menu,
    SettingsMain,
    SettingsDebug,
    SettingsControls,
    PauseMenu,
    LoadoutSelect,
    LevelSelect,
    ControlScreen,
    Countdown,
    Playing,
    Playthrough,  // Non-rendering "referee" state: decides win/lose/next-level/lives.
    InfoScreen,
    EndScreen,
    Exit,
};

}  // namespace tank::core
