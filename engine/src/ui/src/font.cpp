#include "tank/ui/font.hpp"

#include <SDL3/SDL.h>
#include <SDL3_ttf/SDL_ttf.h>

namespace tank::ui {

Font::Font(const std::string& path, float point_size) {
    if (!TTF_WasInit()) {
        TTF_Init();
    }
    font_ = TTF_OpenFont(path.c_str(), point_size);
    if (font_ == nullptr) {
        SDL_Log("Font: failed to open '%s': %s", path.c_str(), SDL_GetError());
    }
}

Font::~Font() {
    for (auto& [text, texture] : cache_) {
        (void)text;
        if (texture != nullptr) {
            SDL_DestroyTexture(texture);
        }
    }
    if (font_ != nullptr) {
        TTF_CloseFont(font_);
    }
}

SDL_Texture* Font::GetTextTexture(SDL_Renderer* renderer, const std::string& text) {
    if (font_ == nullptr || text.empty()) {
        return nullptr;
    }
    if (const auto it = cache_.find(text); it != cache_.end()) {
        return it->second;
    }

    constexpr SDL_Color kWhite{255, 255, 255, 255};
    SDL_Surface* surface = TTF_RenderText_Blended(font_, text.c_str(), text.size(), kWhite);
    if (surface == nullptr) {
        SDL_Log("Font: failed to render '%s': %s", text.c_str(), SDL_GetError());
        return nullptr;
    }
    SDL_Texture* texture = SDL_CreateTextureFromSurface(renderer, surface);
    SDL_DestroySurface(surface);
    cache_[text] = texture;
    return texture;
}

}  // namespace tank::ui
