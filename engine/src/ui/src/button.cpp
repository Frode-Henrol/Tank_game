#include "tank/ui/button.hpp"

#include <algorithm>

#include <SDL3/SDL.h>

namespace tank::ui {

bool Button::Contains(float mouse_x, float mouse_y) const {
    return mouse_x >= x && mouse_x <= x + width && mouse_y >= y && mouse_y <= y + height;
}

void HandleMouseMotion(Button& button, float mouse_x, float mouse_y) {
    button.hovered = !button.disabled && button.Contains(mouse_x, mouse_y);
}

std::optional<tank::core::State> HandleMouseDown(Button& button, float mouse_x, float mouse_y) {
    if (button.disabled || !button.Contains(mouse_x, mouse_y)) {
        return std::nullopt;
    }
    if (button.is_toggle) {
        button.toggle_on = !button.toggle_on;
    }
    // Captured before invoking action(): an action is allowed to rebuild the very container
    // `button` lives in (e.g. transitioning state and re-laying-out the button list), which
    // would leave `button` dangling for anything read from it afterward.
    const std::optional<tank::core::State> target_state = button.target_state;
    if (button.action) {
        button.action();
    }
    return target_state;
}

void DrawButton(SDL_Renderer* renderer, Font& font, const Button& button) {
    // Color precedence matches the original: disabled > hover(brightened) > toggle-on > normal.
    float r = 100.0f / 255.0f, g = 100.0f / 255.0f, b = 200.0f / 255.0f;  // default_color_normal
    if (button.disabled) {
        r = g = b = 150.0f / 255.0f;
    } else if (button.toggle_on) {
        r = 50.0f / 255.0f;
        g = 50.0f / 255.0f;
        b = 150.0f / 255.0f;  // default_color_clicked
    }
    if (button.hovered) {
        r = std::min(r + 50.0f / 255.0f, 1.0f);
        g = std::min(g + 50.0f / 255.0f, 1.0f);
        b = std::min(b + 50.0f / 255.0f, 1.0f);
    }

    SDL_SetRenderDrawColorFloat(renderer, r, g, b, 1.0f);
    const SDL_FRect rect{button.x, button.y, button.width, button.height};
    SDL_RenderFillRect(renderer, &rect);
    SDL_SetRenderDrawColorFloat(renderer, 0.0f, 0.0f, 0.0f, 1.0f);
    SDL_RenderRect(renderer, &rect);

    if (button.text.empty()) {
        return;
    }
    SDL_Texture* text_texture = font.GetTextTexture(renderer, button.text);
    if (text_texture == nullptr) {
        return;
    }
    float text_w = 0.0f;
    float text_h = 0.0f;
    SDL_GetTextureSize(text_texture, &text_w, &text_h);
    const SDL_FRect dst{button.x + (button.width - text_w) / 2.0f, button.y + (button.height - text_h) / 2.0f, text_w,
                         text_h};
    SDL_RenderTexture(renderer, text_texture, nullptr, &dst);
}

}  // namespace tank::ui
