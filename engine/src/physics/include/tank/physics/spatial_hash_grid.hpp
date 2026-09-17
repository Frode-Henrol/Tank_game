#pragma once

#include <cstdint>
#include <unordered_map>
#include <utility>
#include <vector>

#include "tank/ecs/vec2.hpp"

namespace tank::physics {

using tank::ecs::Vec2;

// Uniform spatial hash grid over axis-aligned bounding boxes, keyed by an opaque caller-defined
// `item_id` (an obstacle-edge index, an entt::entity cast to uint32_t, etc.). This is the
// scalability upgrade over the original's "every tank checks every obstacle edge, every tank
// checks every other tank, every frame" O(n*m) scans: build once per level load for static
// obstacle edges, rebuild once per tick for dynamic entities, then only narrow-phase-test items
// whose cell overlaps the query region.
//
// An item whose AABB spans multiple cells is stored in each of them, so a query can visit the
// same item_id more than once - callers doing narrow-phase segment/distance tests are expected
// to tolerate that (the test itself is cheap and idempotent) rather than this class paying for
// a dedupe set on every query.
class SpatialHashGrid {
public:
    explicit SpatialHashGrid(float cell_size);

    void Clear();
    void Insert(std::uint32_t item_id, const Vec2& aabb_min, const Vec2& aabb_max);

    template <typename Visitor>
    void ForEachInRegion(const Vec2& aabb_min, const Vec2& aabb_max, Visitor&& visitor) const {
        const auto [cx_min, cy_min] = CellCoords(aabb_min);
        const auto [cx_max, cy_max] = CellCoords(aabb_max);

        for (int cy = cy_min; cy <= cy_max; ++cy) {
            for (int cx = cx_min; cx <= cx_max; ++cx) {
                const auto it = cells_.find(CellKey(cx, cy));
                if (it == cells_.end()) {
                    continue;
                }
                for (std::uint32_t item_id : it->second) {
                    visitor(item_id);
                }
            }
        }
    }

private:
    float cell_size_;
    std::unordered_map<std::int64_t, std::vector<std::uint32_t>> cells_;

    [[nodiscard]] std::pair<int, int> CellCoords(const Vec2& point) const;
    [[nodiscard]] static std::int64_t CellKey(int cx, int cy);
};

}  // namespace tank::physics
