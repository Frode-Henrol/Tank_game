#include "tank/physics/obstacle_world.hpp"

namespace tank::physics {

ObstacleWorld::ObstacleWorld(float grid_cell_size) : grid_(grid_cell_size) {}

void ObstacleWorld::SetObstacles(std::vector<Obstacle> obstacles) {
    obstacles_ = std::move(obstacles);
    RebuildGrid();
}

void ObstacleWorld::DestroyObstacle(std::size_t obstacle_index) {
    if (obstacle_index >= obstacles_.size()) {
        return;
    }
    obstacles_[obstacle_index].destroyed = true;
    RebuildGrid();
}

void ObstacleWorld::RebuildGrid() {
    grid_.Clear();
    edge_refs_.clear();

    for (std::size_t obstacle_index = 0; obstacle_index < obstacles_.size(); ++obstacle_index) {
        const Obstacle& obstacle = obstacles_[obstacle_index];
        if (obstacle.destroyed) {
            continue;
        }
        for (const auto& [start, end] : PolygonEdges(obstacle.polygon)) {
            const std::uint32_t edge_id = static_cast<std::uint32_t>(edge_refs_.size());
            edge_refs_.push_back(EdgeRef{obstacle_index, start, end});

            const Vec2 aabb_min{std::min(start.x, end.x), std::min(start.y, end.y)};
            const Vec2 aabb_max{std::max(start.x, end.x), std::max(start.y, end.y)};
            grid_.Insert(edge_id, aabb_min, aabb_max);
        }
    }
}

}  // namespace tank::physics
