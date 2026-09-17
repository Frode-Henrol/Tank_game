#include "tank/sim/movement_system.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>

#include "tank/ecs/gameplay_components.hpp"

namespace tank::sim {

using tank::ecs::MovementIntent;
using tank::ecs::PreviousPosition;
using tank::ecs::Transform;
using tank::ecs::TrackedMovement;
using tank::ecs::Vec2;

namespace {

constexpr float kDegToRad = std::numbers::pi_v<float> / 180.0f;

float WrapDegrees(float degrees) {
    float wrapped = std::fmod(degrees, 360.0f);
    if (wrapped < 0.0f) {
        wrapped += 360.0f;
    }
    return wrapped;
}

// Shortest signed delta from `from` to `to`, in (-180, 180].
float ShortestAngleDelta(float from, float to) {
    float delta = std::fmod(to - from + 180.0f, 360.0f) - 180.0f;
    if (delta < -180.0f) {
        delta += 360.0f;
    }
    return delta;
}

}  // namespace

void TrackedMovementSystem::Update(entt::registry& registry, float delta_time_sec) {
    auto view = registry.view<Transform, TrackedMovement, MovementIntent>();
    for (auto entity : view) {
        auto& transform = view.get<Transform>(entity);
        const auto& movement = view.get<TrackedMovement>(entity);
        const auto& intent = view.get<MovementIntent>(entity);

        if (auto* previous = registry.try_get<PreviousPosition>(entity)) {
            previous->position = transform.position;
        }

        if (intent.has_turn_target) {
            const float delta = ShortestAngleDelta(transform.heading_deg, intent.turn_towards_deg);
            const float max_turn = movement.turn_rate_deg * delta_time_sec;
            const float turn = std::clamp(delta, -max_turn, max_turn);
            transform.heading_deg = WrapDegrees(transform.heading_deg + turn);
        } else if (intent.turn_axis != 0.0f) {
            transform.heading_deg =
                WrapDegrees(transform.heading_deg + intent.turn_axis * movement.turn_rate_deg * delta_time_sec);
        }

        if (intent.throttle != 0.0f) {
            const float rads = transform.heading_deg * kDegToRad;
            const Vec2 direction{std::cos(rads), std::sin(rads)};
            transform.position += direction * (intent.throttle * movement.max_speed * delta_time_sec);
        }
    }
}

}  // namespace tank::sim
