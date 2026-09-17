#pragma once

#include <optional>
#include <utility>
#include <vector>

#include "tank/ecs/vec2.hpp"

namespace tank::physics {

using tank::ecs::Vec2;

// A simple polygon as an ordered ring of points (not explicitly closed - the last point
// connects back to the first). Matches the map file's polygon representation.
using Polygon = std::vector<Vec2>;

// Segment start/end pairs for every edge of the polygon, closing the loop (edge N-1 -> 0).
// Mirrors the Python port's helper_functions.coord_to_coordlist().
[[nodiscard]] std::vector<std::pair<Vec2, Vec2>> PolygonEdges(const Polygon& polygon);

// Intersection point of segments (a1,a2) and (b1,b2), or std::nullopt if they don't cross.
// AABB early-rejection + Cramer's rule, same tolerance/algorithm as the original's Cython
// line_intersection() (the hottest routine in the sim: every hitbox edge x every wall edge x
// every tank, every tick, plus all AI ray/line-of-sight checks).
[[nodiscard]] std::optional<Vec2> SegmentIntersection(const Vec2& a1, const Vec2& a2, const Vec2& b1, const Vec2& b2);

// Both unit normals perpendicular to the edge (start -> end), caller picks whichever faces the
// incoming direction via a negative dot product. Matches deflect.py's find_normal_vectors().
[[nodiscard]] std::pair<Vec2, Vec2> EdgeNormals(const Vec2& start, const Vec2& end);

// Reflects `direction` off a surface with the given unit normal: v' = v - 2(v.n)n. No
// restitution - this is the single reflection law shared by tank wall push-back, projectile
// bounces, and AI ray-bounce shot prediction; keep all three using this one function so they
// can never quietly diverge from each other.
[[nodiscard]] Vec2 Reflect(const Vec2& direction, const Vec2& normal);

// Shortest (unsigned) distance from `point` to the infinite line through (a, b). Callers that
// need segment semantics must separately verify the point projects onto the segment - this
// intentionally mirrors the original's point_to_line_distance(), which the AI targeting code
// relies on being "infinite line" semantics.
[[nodiscard]] float DistanceToLine(const Vec2& a, const Vec2& b, const Vec2& point);

// True if `point`'s projection onto segment (a, b) falls between the endpoints (not "on the
// line" - purely the projection/parameterization check).
[[nodiscard]] bool IsBetweenSegment(const Vec2& a, const Vec2& b, const Vec2& point);

// Ray-cast point-in-polygon test (even-odd rule) against a possibly-concave polygon. The test
// ray is cast along a fixed non-axis-aligned direction to avoid the classic degeneracies
// (ray-through-vertex, ray-coincident-with-a-horizontal-edge) that hand-authored map grids hit
// more often than random data would - see the architecture plan's pathfinding section.
[[nodiscard]] bool PointInPolygon(const Polygon& polygon, const Vec2& point);

// True if `a` is to the left of the directed line from `p` to `q` (2D cross-product sign test).
// Used throughout for turn-direction decisions (steering, AI turret rotation direction).
[[nodiscard]] bool LeftTurn(const Vec2& p, const Vec2& q, const Vec2& r);

}  // namespace tank::physics
