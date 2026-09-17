#include "tank/render/polygon_renderer.hpp"

#include <SDL3/SDL.h>

namespace tank::render {

void DrawFilledPolygon(SDL_Renderer* renderer, const std::vector<Vec2>& polygon, Color color) {
    if (polygon.size() < 3) {
        return;
    }

    std::vector<SDL_Vertex> vertices;
    vertices.reserve(polygon.size());
    const SDL_FColor sdl_color{color.r, color.g, color.b, color.a};
    for (const Vec2& point : polygon) {
        vertices.push_back(SDL_Vertex{SDL_FPoint{point.x, point.y}, sdl_color, SDL_FPoint{0.0f, 0.0f}});
    }

    std::vector<int> indices;
    indices.reserve((polygon.size() - 2) * 3);
    for (std::size_t i = 1; i + 1 < polygon.size(); ++i) {
        indices.push_back(0);
        indices.push_back(static_cast<int>(i));
        indices.push_back(static_cast<int>(i + 1));
    }

    SDL_RenderGeometry(renderer, nullptr, vertices.data(), static_cast<int>(vertices.size()), indices.data(),
                        static_cast<int>(indices.size()));
}

}  // namespace tank::render
