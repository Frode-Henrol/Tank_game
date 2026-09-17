#pragma once

#include <cstddef>
#include <optional>
#include <vector>

#include "tank/ecs/vec2.hpp"
#include "tank/physics/obstacle.hpp"

namespace tank::ai {

using tank::ecs::Vec2;

struct GridCoord {
    int x = 0;
    int y = 0;
};

inline bool operator==(const GridCoord& a, const GridCoord& b) { return a.x == b.x && a.y == b.y; }

// A uniform grid over a level's playable area: A* pathfinding and "find a valid node near this
// point" queries (patrol/defend-ring/dodge target selection) both run against it. Built once
// per level load from the border plus every obstacle polygon - pits and destructibles block
// *pathfinding* exactly like standard walls, even though they don't all block projectiles (a
// tank still can't physically stand in a pit or drive through an unexploded destructible);
// destroying a destructible obstacle later does not currently reopen the grid, matching the
// original's static-per-level nav grid.
//
// Deliberately has no separate spatial-index data structure (no KD-tree): since nodes already
// live on a uniform grid, a radius query is direct index-range math over neighboring cells.
class NavGrid {
public:
    NavGrid(const Vec2& top_left, const Vec2& bottom_right, float node_spacing,
            const std::vector<physics::Obstacle>& obstacles);

    [[nodiscard]] GridCoord WorldToGrid(const Vec2& world) const;
    [[nodiscard]] Vec2 GridToWorld(const GridCoord& coord) const;
    [[nodiscard]] bool IsValid(const GridCoord& coord) const;

    // A* path between two world-space points, returned as world-space waypoints (cell centers).
    // Start/end are snapped to the nearest valid node. std::nullopt if no path exists (or if no
    // valid node could be found near either endpoint).
    [[nodiscard]] std::optional<std::vector<Vec2>> FindPath(const Vec2& from, const Vec2& to) const;

    // Every valid node's world position within `radius` of `center`.
    [[nodiscard]] std::vector<Vec2> FindValidNodesNear(const Vec2& center, float radius) const;

private:
    Vec2 top_left_;
    float node_spacing_;
    int width_ = 0;
    int height_ = 0;
    std::vector<bool> blocked_;  // width_ * height_, row-major

    [[nodiscard]] std::size_t Index(const GridCoord& coord) const;
    [[nodiscard]] std::optional<GridCoord> NearestValid(const Vec2& world) const;
};

}  // namespace tank::ai
