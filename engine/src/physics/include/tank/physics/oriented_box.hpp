#pragma once

#include <array>
#include <utility>
#include <vector>

#include "tank/ecs/vec2.hpp"

namespace tank::physics {

using tank::ecs::Vec2;

// Precomputes rotated unit-box corners bucketed by heading, so looking up "this box's corners
// at roughly this heading" is an O(1) table lookup with no per-query trig - the same trick the
// original used for its (fixed 40x40) tank hitbox, generalized here to work for any box size:
// the cache stores only the *unit* box (half-extent 1 on each axis) rotated per bucket; callers
// scale by their own half_width/half_height and translate to their own center. One shared cache
// instance (see BoxCorners()) serves every entity regardless of its individual collision size.
class OrientedBoxCache {
public:
    explicit OrientedBoxCache(float angle_step_deg = 5.0f);

    [[nodiscard]] const std::array<Vec2, 4>& UnitCorners(float heading_deg) const;

private:
    float angle_step_deg_;
    std::vector<std::array<Vec2, 4>> buckets_;
};

// World-space corners (front-left, front-right, back-right, back-left, matching the original's
// winding) of a `half_width` x `half_height` box centered at `center`, rotated to `heading_deg`.
[[nodiscard]] std::array<Vec2, 4> BoxCorners(const OrientedBoxCache& cache, const Vec2& center, float half_width,
                                              float half_height, float heading_deg);

// The 4 edges of a box's corners, closing the loop - ready to feed to SegmentIntersection().
[[nodiscard]] std::array<std::pair<Vec2, Vec2>, 4> BoxEdges(const std::array<Vec2, 4>& corners);

}  // namespace tank::physics
