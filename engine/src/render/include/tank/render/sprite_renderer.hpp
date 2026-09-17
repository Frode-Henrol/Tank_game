#pragma once

struct SDL_Renderer;

namespace tank::ecs {
struct Transform;
struct Sprite;
}  // namespace tank::ecs

namespace tank::render {

class TextureCache;

// Draws one Transform+Sprite pair: rotate-and-blit, matching the original's
// pygame.transform.rotate + blit-centered-on-position model.
void DrawSprite(SDL_Renderer* renderer, TextureCache& textures, const tank::ecs::Transform& transform,
                 const tank::ecs::Sprite& sprite);

}  // namespace tank::render
