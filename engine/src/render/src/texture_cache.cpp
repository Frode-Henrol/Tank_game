#include "tank/render/texture_cache.hpp"

#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>

namespace tank::render {

TextureCache::~TextureCache() {
    for (auto& [path, texture] : textures_) {
        (void)path;
        if (texture != nullptr) {
            SDL_DestroyTexture(texture);
        }
    }
}

SDL_Texture* TextureCache::Get(const std::string& path) {
    if (auto it = textures_.find(path); it != textures_.end()) {
        return it->second;
    }

    SDL_Texture* texture = IMG_LoadTexture(renderer_, path.c_str());
    if (texture == nullptr) {
        SDL_Log("Failed to load texture '%s': %s", path.c_str(), SDL_GetError());
    }
    textures_.emplace(path, texture);
    return texture;
}

}  // namespace tank::render
