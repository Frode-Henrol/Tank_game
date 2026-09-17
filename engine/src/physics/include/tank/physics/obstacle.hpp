#pragma once

#include <cstdint>

#include "tank/physics/geometry.hpp"

namespace tank::physics {

// Matches the original map format's polygon type codes exactly (0/1/2), so the map parser can
// cast the on-disk integer directly.
enum class ObstacleType : std::uint8_t {
    Standard = 0,     // blocks tanks and projectiles
    Destructible = 1, // blocks tanks and projectiles until a mine/explosion removes it
    Pit = 2,          // blocks tanks only - NOT projectiles (a real asymmetry in the original,
                       // preserved deliberately rather than "fixed")
};

struct Obstacle {
    Polygon polygon;
    ObstacleType type = ObstacleType::Standard;
    bool destroyed = false;  // Destructible only; once true, excluded from collision + rendering
};

}  // namespace tank::physics
