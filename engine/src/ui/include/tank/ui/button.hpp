#pragma once

#include <functional>
#include <optional>
#include <string>

#include "tank/core/state.hpp"
#include "tank/ui/font.hpp"

struct SDL_Renderer;

namespace tank::ui {

// A plain data + free-function widget (matching this codebase's ECS-adjacent style rather than
// a heavier OOP widget hierarchy) - equivalent to the original's Button class: position/size/
// text/optional target-state/optional click action, hover highlight, disabled and toggle-on
// states.
struct Button {
    float x = 0.0f;
    float y = 0.0f;
    float width = 0.0f;
    float height = 0.0f;
    std::string text;
    std::optional<tank::core::State> target_state;
    std::function<void()> action;
    bool is_toggle = false;
    bool toggle_on = false;
    bool disabled = false;
    bool hovered = false;  // Updated by HandleMouseMotion; read by DrawButton for the hover tint.

    [[nodiscard]] bool Contains(float mouse_x, float mouse_y) const;
};

void HandleMouseMotion(Button& button, float mouse_x, float mouse_y);

// Fires `action` (if set) then returns `target_state` (if set) - matching the original's
// handle_event(): action runs before any state transition. Returns std::nullopt (and does
// nothing else) if the click missed the button or it's disabled.
//
// `target_state` is captured before `action` runs, so an action MAY rebuild the container this
// Button lives in (e.g. an app-level transition that re-lays-out the current screen's buttons)
// without leaving this call's `button` reference dangling - but `action` itself must never do
// that rebuild synchronously and then have this function read `button` again afterward, which is
// exactly what the capture-before-call ordering avoids. Conversely, an action must not assume it
// can safely reuse `button` after triggering such a rebuild.
std::optional<tank::core::State> HandleMouseDown(Button& button, float mouse_x, float mouse_y);

void DrawButton(SDL_Renderer* renderer, Font& font, const Button& button);

}  // namespace tank::ui
