#pragma once

#include <algorithm>
#include <cstdint>
#include <vector>

#include "tank/physics/obstacle.hpp"
#include "tank/physics/spatial_hash_grid.hpp"

namespace tank::physics {

// Owns a level's static obstacle geometry plus a spatial hash grid over its edges, so "which
// obstacle edges are near this point/box" is a grid query instead of a scan over every
// obstacle - the main scalability upgrade over the original's O(n*m) per-frame edge scan.
class ObstacleWorld {
public:
    explicit ObstacleWorld(float grid_cell_size = 150.0f);

    void SetObstacles(std::vector<Obstacle> obstacles);
    [[nodiscard]] const std::vector<Obstacle>& Obstacles() const { return obstacles_; }
    [[nodiscard]] std::vector<Obstacle>& MutableObstacles() { return obstacles_; }

    // Marks a Destructible obstacle removed (mine/explosion). Rebuilds the grid, since removals
    // are rare (a handful per level at most) compared to per-tick collision queries.
    void DestroyObstacle(std::size_t obstacle_index);

    // Visits every (obstacle_index, edge_start, edge_end) whose edge-cell overlaps the given
    // AABB, skipping destroyed obstacles and, unless `include_pits` is set, Pit-type ones - the
    // original never tests projectiles against pits (tanks-only hazard), an asymmetry preserved
    // here rather than "fixed".
    template <typename Visitor>
    void QueryEdgesNear(const Vec2& aabb_min, const Vec2& aabb_max, bool include_pits, Visitor&& visitor) const {
        grid_.ForEachInRegion(aabb_min, aabb_max, [&](std::uint32_t edge_id) {
            const EdgeRef& ref = edge_refs_[edge_id];
            const Obstacle& obstacle = obstacles_[ref.obstacle_index];
            if (obstacle.destroyed) {
                return;
            }
            if (!include_pits && obstacle.type == ObstacleType::Pit) {
                return;
            }
            visitor(ref.obstacle_index, ref.start, ref.end);
        });
    }

private:
    struct EdgeRef {
        std::size_t obstacle_index;
        Vec2 start;
        Vec2 end;
    };

    void RebuildGrid();

    std::vector<Obstacle> obstacles_;
    std::vector<EdgeRef> edge_refs_;
    SpatialHashGrid grid_;
};

}  // namespace tank::physics
