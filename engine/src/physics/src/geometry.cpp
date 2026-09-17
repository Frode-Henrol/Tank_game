#include "tank/physics/geometry.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace tank::physics {

namespace {
constexpr float kEpsilon = 1e-9f;
}

std::vector<std::pair<Vec2, Vec2>> PolygonEdges(const Polygon& polygon) {
    std::vector<std::pair<Vec2, Vec2>> edges;
    if (polygon.size() < 2) {
        return edges;
    }
    edges.reserve(polygon.size());
    for (std::size_t i = 0; i < polygon.size(); ++i) {
        const Vec2& start = polygon[i];
        const Vec2& end = polygon[(i + 1) % polygon.size()];
        edges.emplace_back(start, end);
    }
    return edges;
}

std::optional<Vec2> SegmentIntersection(const Vec2& a1, const Vec2& a2, const Vec2& b1, const Vec2& b2) {
    const float a_min_x = std::min(a1.x, a2.x);
    const float a_max_x = std::max(a1.x, a2.x);
    const float a_min_y = std::min(a1.y, a2.y);
    const float a_max_y = std::max(a1.y, a2.y);
    const float b_min_x = std::min(b1.x, b2.x);
    const float b_max_x = std::max(b1.x, b2.x);
    const float b_min_y = std::min(b1.y, b2.y);
    const float b_max_y = std::max(b1.y, b2.y);

    // Early AABB rejection.
    if (a_max_x < b_min_x || a_min_x > b_max_x || a_max_y < b_min_y || a_min_y > b_max_y) {
        return std::nullopt;
    }

    const float denominator = (a1.x - a2.x) * (b1.y - b2.y) - (a1.y - a2.y) * (b1.x - b2.x);
    if (denominator == 0.0f) {
        return std::nullopt;  // Parallel or coincident.
    }

    const float det_a = a1.x * a2.y - a1.y * a2.x;
    const float det_b = b1.x * b2.y - b1.y * b2.x;

    const float px = (det_a * (b1.x - b2.x) - (a1.x - a2.x) * det_b) / denominator;
    const float py = (det_a * (b1.y - b2.y) - (a1.y - a2.y) * det_b) / denominator;

    if (px >= a_min_x - kEpsilon && px <= a_max_x + kEpsilon && py >= a_min_y - kEpsilon && py <= a_max_y + kEpsilon &&
        px >= b_min_x - kEpsilon && px <= b_max_x + kEpsilon && py >= b_min_y - kEpsilon && py <= b_max_y + kEpsilon) {
        return Vec2{px, py};
    }
    return std::nullopt;
}

std::pair<Vec2, Vec2> EdgeNormals(const Vec2& start, const Vec2& end) { return (end - start).PerpendicularPair(); }

Vec2 Reflect(const Vec2& direction, const Vec2& normal) {
    const float d = direction.Dot(normal);
    return direction - normal * (2.0f * d);
}

float DistanceToLine(const Vec2& a, const Vec2& b, const Vec2& point) {
    const float numerator = std::abs((b.y - a.y) * point.x - (b.x - a.x) * point.y + b.x * a.y - b.y * a.x);
    const float denominator = std::sqrt((b.y - a.y) * (b.y - a.y) + (b.x - a.x) * (b.x - a.x));
    return denominator != 0.0f ? numerator / denominator : std::numeric_limits<float>::infinity();
}

bool IsBetweenSegment(const Vec2& a, const Vec2& b, const Vec2& point) {
    const Vec2 segment = b - a;
    const Vec2 to_point = point - a;
    const float dot = segment.Dot(to_point);
    if (dot < 0.0f) {
        return false;
    }
    return to_point.LengthSquared() <= segment.LengthSquared();
}

bool PointInPolygon(const Polygon& polygon, const Vec2& point) {
    if (polygon.size() < 3) {
        return false;
    }

    // A tiny fixed jitter on the query point dodges the classic ray-through-vertex /
    // ray-coincident-with-horizontal-edge degeneracies that axis-aligned pathfinding grid
    // nodes hit far more often than random data would.
    const Vec2 test{point.x + 0.0137f, point.y + 0.0251f};

    bool inside = false;
    for (std::size_t i = 0, j = polygon.size() - 1; i < polygon.size(); j = i++) {
        const Vec2& vi = polygon[i];
        const Vec2& vj = polygon[j];
        const bool crosses = (vi.y > test.y) != (vj.y > test.y);
        if (crosses) {
            const float x_intersect = (vj.x - vi.x) * (test.y - vi.y) / (vj.y - vi.y) + vi.x;
            if (test.x < x_intersect) {
                inside = !inside;
            }
        }
    }
    return inside;
}

bool LeftTurn(const Vec2& p, const Vec2& q, const Vec2& r) {
    return (q.x - p.x) * (r.y - p.y) - (r.x - p.x) * (q.y - p.y) >= 0.0f;
}

}  // namespace tank::physics
