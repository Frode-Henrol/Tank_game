#include "tank/core/app.hpp"

#include <SDL3/SDL.h>

namespace tank::core {

App::App(tank::render::Window& window, float fixed_dt_sec) : window_(window), fixed_dt_sec_(fixed_dt_sec) {}

void App::Run() {
    const Uint64 frequency = SDL_GetPerformanceFrequency();
    Uint64 last_counter = SDL_GetPerformanceCounter();
    float accumulator = 0.0f;

    while (!quit_requested_) {
        const Uint64 now = SDL_GetPerformanceCounter();
        const float elapsed = static_cast<float>(now - last_counter) / static_cast<float>(frequency);
        last_counter = now;
        accumulator += elapsed;

        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_EVENT_QUIT) {
                quit_requested_ = true;
            } else if (event.type == SDL_EVENT_KEY_DOWN) {
                if (key_down_fn_) {
                    key_down_fn_(static_cast<int>(event.key.scancode));
                }
            } else if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN) {
                if (mouse_down_fn_) {
                    mouse_down_fn_(event.button.x, event.button.y, static_cast<int>(event.button.button));
                }
            }
        }

        // Guard against a huge stall (breakpoint, window drag, etc.) turning into a spiral of
        // fixed updates endlessly trying to catch up.
        constexpr float kMaxAccumulator = 0.25f;
        if (accumulator > kMaxAccumulator) {
            accumulator = kMaxAccumulator;
        }

        while (accumulator >= fixed_dt_sec_) {
            if (update_fn_) {
                update_fn_(state_, fixed_dt_sec_);
            }
            accumulator -= fixed_dt_sec_;
        }

        if (render_fn_) {
            render_fn_(state_);
        }
        window_.Present();
    }
}

}  // namespace tank::core
