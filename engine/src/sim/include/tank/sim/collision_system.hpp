#pragma once

#include <entt/entity/registry.hpp>

#include "tank/physics/obstacle_world.hpp"
#include "tank/physics/oriented_box.hpp"

namespace tank::sim {

// Pushes any (Transform, CollisionShape, TrackedMovement) entity back out of walls it's driven
// into. Matches the original's push-back rule exactly: always along the wall edge's *second*
// normal (physics::EdgeNormals(...).second), not "whichever normal faces the tank" - safe only
// because the map format requires polygons to be wound clockwise (see the README), which makes
// that second normal consistently point outward regardless of which edge or approach angle was
// hit. Push magnitude is `max_speed * dt` (the tank's nominal per-tick travel distance),
// applied regardless of current throttle - matching the original applying it unconditionally.
class WallCollisionSystem {
public:
    explicit WallCollisionSystem(const physics::OrientedBoxCache& box_cache) : box_cache_(&box_cache) {}

    void Update(entt::registry& registry, const physics::ObstacleWorld& world, float dt);

private:
    const physics::OrientedBoxCache* box_cache_;
};

// Symmetric separation push between any two overlapping (Transform, CollisionShape) entities -
// same formula as the original's apply_repulsion() (primary push along the separation vector
// plus a 20%-strength perpendicular component), applied to both entities in a pair. Unlike the
// original, this does not special-case immovable (max_speed == 0) entities by corrupting their
// direction/speed as a side effect - that was a workaround specific to the original's wall
// push-back formula depending on `speed`, which this repulsion formula never did in the first
// place, so the workaround has nothing to compensate for here.
class TankRepulsionSystem {
public:
    void Update(entt::registry& registry, float dt);
};

}  // namespace tank::sim
