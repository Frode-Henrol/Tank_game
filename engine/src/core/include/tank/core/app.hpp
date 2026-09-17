#pragma once

#include <functional>

#include "tank/core/state.hpp"
#include "tank/render/window.hpp"

namespace tank::core {

// Generic fixed-timestep application shell. Owns the window, the current State, and the main
// loop; has zero gameplay logic of its own - all per-state behavior is supplied by the
// callbacks below. Every state (including menus, countdown, info-screen, etc.) is ticked once
// per frame from this one loop; there are no nested blocking loops with their own clocks.
class App {
public:
    // Called at a fixed rate (see fixed_dt_sec passed to the constructor), possibly multiple
    // times per rendered frame (or zero times, if a frame renders faster than the fixed step).
    using UpdateFn = std::function<void(State state, float fixed_dt_sec)>;
    // Called exactly once per rendered frame, after all pending fixed updates for that frame.
    using RenderFn = std::function<void(State state)>;
    // Called once per SDL_EVENT_KEY_DOWN, for discrete (non-continuous) input. Escape has no
    // built-in meaning here (deliberately - it needs to mean "pause" during Playing and
    // "back"/"quit" elsewhere, which only the app layer's per-state logic can decide); the app
    // must call RequestQuit() itself when it actually wants to exit.
    using KeyDownFn = std::function<void(int scancode)>;
    // Called once per SDL_EVENT_MOUSE_BUTTON_DOWN, for UI widget clicks (button is an
    // SDL_BUTTON_LEFT/RIGHT/etc index).
    using MouseDownFn = std::function<void(float x, float y, int button)>;

    App(tank::render::Window& window, float fixed_dt_sec);

    void SetUpdateCallback(UpdateFn fn) { update_fn_ = std::move(fn); }
    void SetRenderCallback(RenderFn fn) { render_fn_ = std::move(fn); }
    void SetKeyDownCallback(KeyDownFn fn) { key_down_fn_ = std::move(fn); }
    void SetMouseDownCallback(MouseDownFn fn) { mouse_down_fn_ = std::move(fn); }

    void SetState(State state) { state_ = state; }
    [[nodiscard]] State CurrentState() const { return state_; }

    void RequestQuit() { quit_requested_ = true; }

    // Runs the loop until quit is requested (window close or RequestQuit()).
    void Run();

private:
    tank::render::Window& window_;
    float fixed_dt_sec_;
    State state_ = State::Menu;
    bool quit_requested_ = false;

    UpdateFn update_fn_;
    RenderFn render_fn_;
    KeyDownFn key_down_fn_;
    MouseDownFn mouse_down_fn_;
};

}  // namespace tank::core
