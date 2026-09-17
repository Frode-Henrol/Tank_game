#include "tank/render/sprite_renderer.hpp"

#include <SDL3/SDL.h>

#include "tank/ecs/gameplay_components.hpp"
#include "tank/render/texture_cache.hpp"

namespace tank::render {

void DrawSprite(SDL_Renderer* renderer, TextureCache& textures, const tank::ecs::Transform& transform,
                 const tank::ecs::Sprite& sprite) {
    SDL_Texture* texture = textures.Get(sprite.texture_id);
    if (texture == nullptr) {
        return;
    }

    const SDL_FRect dst{
        transform.position.x - sprite.width * sprite.pivot_x,
        transform.position.y - sprite.height * sprite.pivot_y,
        sprite.width,
        sprite.height,
    };
    const SDL_FPoint center{sprite.width * sprite.pivot_x, sprite.height * sprite.pivot_y};

    // World heading is degrees CCW from +x (atan2 convention); SDL's rotation angle is degrees
    // clockwise from the destination rect's unrotated orientation, hence the sign flip.
    const double angle = static_cast<double>(transform.heading_deg + sprite.rotation_offset_deg);
    SDL_RenderTextureRotated(renderer, texture, nullptr, &dst, angle, &center, SDL_FLIP_NONE);
}

}  // namespace tank::render
