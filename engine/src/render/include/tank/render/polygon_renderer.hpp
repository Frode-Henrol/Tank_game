#pragma once

#include <vector>

#include "tank/ecs/vec2.hpp"

struct SDL_Renderer;

namespace tank::render {

using tank::ecs::Vec2;

struct Color {
    float r, g, b, a = 1.0f;
};

// Fills a convex polygon via fan triangulation (vertex 0 as the fan's apex) using
// SDL_RenderGeometry. Every obstacle polygon in the existing map files is convex (rectangles),
// so this is sufficient for now - a genuinely concave polygon would need proper ear-clipping,
// which isn't needed until/unless a future map uses one.
void DrawFilledPolygon(SDL_Renderer* renderer, const std::vector<Vec2>& polygon, Color color);

}  // namespace tank::render
