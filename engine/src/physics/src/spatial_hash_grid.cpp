#include "tank/physics/spatial_hash_grid.hpp"

#include <cmath>

namespace tank::physics {

SpatialHashGrid::SpatialHashGrid(float cell_size) : cell_size_(cell_size) {}

void SpatialHashGrid::Clear() { cells_.clear(); }

void SpatialHashGrid::Insert(std::uint32_t item_id, const Vec2& aabb_min, const Vec2& aabb_max) {
    const auto [cx_min, cy_min] = CellCoords(aabb_min);
    const auto [cx_max, cy_max] = CellCoords(aabb_max);

    for (int cy = cy_min; cy <= cy_max; ++cy) {
        for (int cx = cx_min; cx <= cx_max; ++cx) {
            cells_[CellKey(cx, cy)].push_back(item_id);
        }
    }
}

std::pair<int, int> SpatialHashGrid::CellCoords(const Vec2& point) const {
    return {static_cast<int>(std::floor(point.x / cell_size_)), static_cast<int>(std::floor(point.y / cell_size_))};
}

std::int64_t SpatialHashGrid::CellKey(int cx, int cy) {
    // Pack two 32-bit cell coordinates into one 64-bit key.
    return (static_cast<std::int64_t>(cx) << 32) ^ static_cast<std::uint32_t>(cy);
}

}  // namespace tank::physics
