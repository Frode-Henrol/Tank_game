#include "tank/ai/targeting.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

#include "tank/physics/geometry.hpp"

namespace tank::ai {

namespace {
constexpr float kMinSpeed = 1e-4f;
}

Vec2 InterceptPoint(const Vec2& shooter_pos, float projectile_speed, const Vec2& target_pos, const Vec2& target_velocity) {
    const Vec2 rel = target_pos - shooter_pos;
    const float target_speed = target_velocity.Length();
    if (target_speed < kMinSpeed) {
        return target_pos;  // Stationary - nothing to lead.
    }
    const Vec2 d = target_velocity.Normalized();

    const float a = target_speed * target_speed - projectile_speed * projectile_speed;
    const float b = 2.0f * target_speed * rel.Dot(d);
    const float c = rel.Dot(rel);

    float t = -1.0f;
    if (std::fabs(a) < kMinSpeed) {
        // Degenerates to linear (target speed == projectile speed): b*t + c = 0.
        if (std::fabs(b) > kMinSpeed) {
            const float candidate = -c / b;
            if (candidate > 0.0f) {
                t = candidate;
            }
        }
    } else {
        const float discriminant = b * b - 4.0f * a * c;
        if (discriminant >= 0.0f) {
            const float sqrt_disc = std::sqrt(discriminant);
            const float t1 = (-b + sqrt_disc) / (2.0f * a);
            const float t2 = (-b - sqrt_disc) / (2.0f * a);
            for (const float candidate : {t1, t2}) {
                if (candidate > 0.0f && (t < 0.0f || candidate < t)) {
                    t = candidate;
                }
            }
        }
    }

    if (t < 0.0f) {
        return target_pos;  // No positive-time solution - can't intercept.
    }
    return target_pos + d * (target_speed * t);
}

PredictedRay PredictBouncePath(const physics::ObstacleWorld& obstacles, const Vec2& start, const Vec2& direction,
                                int max_bounces, float corner_margin, float max_segment_length) {
    PredictedRay result;

    Vec2 current_point = start;
    Vec2 current_direction = direction.Normalized();
    int bounce_count = 0;

    while (bounce_count <= max_bounces) {
        const Vec2 end_point = current_point + current_direction * max_segment_length;
        const Vec2 seg_min{std::min(current_point.x, end_point.x), std::min(current_point.y, end_point.y)};
        const Vec2 seg_max{std::max(current_point.x, end_point.x), std::max(current_point.y, end_point.y)};

        bool found = false;
        float closest_dist_sq = std::numeric_limits<float>::infinity();
        Vec2 closest_point{};
        Vec2 closest_normal{};
        Vec2 hit_edge_a{};
        Vec2 hit_edge_b{};

        obstacles.QueryEdgesNear(seg_min, seg_max, /*include_pits=*/false,
                                  [&](std::size_t /*obstacle_index*/, const Vec2& a, const Vec2& b) {
                                      const auto intersection = physics::SegmentIntersection(current_point, end_point, a, b);
                                      if (!intersection) {
                                          return;
                                      }
                                      const float dist_sq = (*intersection - current_point).LengthSquared();
                                      if (dist_sq < closest_dist_sq) {
                                          closest_dist_sq = dist_sq;
                                          closest_point = *intersection;
                                          const auto [normal1, normal2] = physics::EdgeNormals(a, b);
                                          closest_normal = current_direction.Dot(normal1) < 0.0f ? normal1 : normal2;
                                          hit_edge_a = a;
                                          hit_edge_b = b;
                                          found = true;
                                      }
                                  });

        if (!found) {
            result.segments.emplace_back(current_point, end_point);
            break;
        }

        result.segments.emplace_back(current_point, closest_point);

        if ((closest_point - hit_edge_a).Length() < corner_margin || (closest_point - hit_edge_b).Length() < corner_margin) {
            result.ambiguous_corner = closest_point;
            return result;
        }

        current_direction = physics::Reflect(current_direction, closest_normal);
        current_point = closest_point + current_direction * 0.1f;
        ++bounce_count;
    }

    return result;
}

bool IsPointNearSegment(const Vec2& a, const Vec2& b, const Vec2& point, float threshold) {
    if (!physics::IsBetweenSegment(a, b, point)) {
        return false;
    }
    return physics::DistanceToLine(a, b, point) < threshold;
}

}  // namespace tank::ai
