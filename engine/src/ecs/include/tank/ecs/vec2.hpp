#pragma once

#include <cmath>
#include <utility>

namespace tank::ecs {

// Plain 2D vector shared by every module (ecs/physics/ai/sim/render). Deliberately not a
// general-purpose math library dependency - the game only ever needs 2D points/directions.
struct Vec2 {
    float x = 0.0f;
    float y = 0.0f;

    constexpr Vec2 operator+(const Vec2& rhs) const { return {x + rhs.x, y + rhs.y}; }
    constexpr Vec2 operator-(const Vec2& rhs) const { return {x - rhs.x, y - rhs.y}; }
    constexpr Vec2 operator*(float s) const { return {x * s, y * s}; }

    constexpr Vec2& operator+=(const Vec2& rhs) {
        x += rhs.x;
        y += rhs.y;
        return *this;
    }

    [[nodiscard]] constexpr float Dot(const Vec2& rhs) const { return x * rhs.x + y * rhs.y; }
    [[nodiscard]] constexpr float LengthSquared() const { return x * x + y * y; }
    [[nodiscard]] float Length() const { return std::sqrt(LengthSquared()); }

    [[nodiscard]] Vec2 Normalized() const {
        const float len = Length();
        if (len <= 1e-9f) {
            return {0.0f, 0.0f};
        }
        return {x / len, y / len};
    }

    // Both unit normals perpendicular to this vector (treated as a direction), matching the
    // Python find_normal_vectors() convention: (-dy, dx) and (dy, -dx).
    [[nodiscard]] std::pair<Vec2, Vec2> PerpendicularPair() const {
        const Vec2 unit = Normalized();
        return {Vec2{-unit.y, unit.x}, Vec2{unit.y, -unit.x}};
    }
};

}  // namespace tank::ecs
