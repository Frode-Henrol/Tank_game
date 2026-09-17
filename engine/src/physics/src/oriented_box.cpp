#include "tank/physics/oriented_box.hpp"

#include <cmath>
#include <numbers>

namespace tank::physics {

namespace {
constexpr float kDegToRad = std::numbers::pi_v<float> / 180.0f;

float WrapDegrees(float degrees) {
    float wrapped = std::fmod(degrees, 360.0f);
    if (wrapped < 0.0f) {
        wrapped += 360.0f;
    }
    return wrapped;
}
}  // namespace

OrientedBoxCache::OrientedBoxCache(float angle_step_deg) : angle_step_deg_(angle_step_deg) {
    const auto bucket_count = static_cast<std::size_t>(360.0f / angle_step_deg_);
    buckets_.reserve(bucket_count);
    for (std::size_t i = 0; i < bucket_count; ++i) {
        const float angle_deg = static_cast<float>(i) * angle_step_deg_;
        const float rads = angle_deg * kDegToRad;
        const float c = std::cos(rads);
        const float s = std::sin(rads);

        // Unit box corners (before rotation): front-left, front-right, back-right, back-left -
        // "front" is +x (heading 0), matching the Transform.heading_deg convention.
        constexpr std::array<Vec2, 4> kUnitBox{
            Vec2{1.0f, -1.0f},
            Vec2{1.0f, 1.0f},
            Vec2{-1.0f, 1.0f},
            Vec2{-1.0f, -1.0f},
        };

        std::array<Vec2, 4> rotated{};
        for (std::size_t corner = 0; corner < 4; ++corner) {
            const Vec2& p = kUnitBox[corner];
            rotated[corner] = Vec2{p.x * c - p.y * s, p.x * s + p.y * c};
        }
        buckets_.push_back(rotated);
    }
}

const std::array<Vec2, 4>& OrientedBoxCache::UnitCorners(float heading_deg) const {
    const float wrapped = WrapDegrees(heading_deg);
    auto index = static_cast<std::size_t>(wrapped / angle_step_deg_);
    if (index >= buckets_.size()) {
        index = 0;
    }
    return buckets_[index];
}

std::array<Vec2, 4> BoxCorners(const OrientedBoxCache& cache, const Vec2& center, float half_width, float half_height,
                                float heading_deg) {
    const auto& unit = cache.UnitCorners(heading_deg);
    return {
        Vec2{center.x + unit[0].x * half_width, center.y + unit[0].y * half_height},
        Vec2{center.x + unit[1].x * half_width, center.y + unit[1].y * half_height},
        Vec2{center.x + unit[2].x * half_width, center.y + unit[2].y * half_height},
        Vec2{center.x + unit[3].x * half_width, center.y + unit[3].y * half_height},
    };
}

std::array<std::pair<Vec2, Vec2>, 4> BoxEdges(const std::array<Vec2, 4>& corners) {
    return {
        std::pair{corners[0], corners[1]},
        std::pair{corners[1], corners[2]},
        std::pair{corners[2], corners[3]},
        std::pair{corners[3], corners[0]},
    };
}

}  // namespace tank::physics
