#include "tank/ai/nav_grid.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <queue>
#include <unordered_map>
#include <utility>

#include "tank/physics/geometry.hpp"

namespace tank::ai {

namespace {

struct GridCoordHash {
    std::size_t operator()(const GridCoord& c) const {
        return std::hash<std::int64_t>()((static_cast<std::int64_t>(c.x) << 32) ^ static_cast<std::uint32_t>(c.y));
    }
};

// 8-connected neighbor offsets + step cost. Diagonal cost is sqrt(2), matching the original's
// grid_to_dict(); diagonal moves additionally require both flanking orthogonal cells to be open
// (checked in FindPath below) so paths can't cut across a wall corner.
constexpr std::array<std::pair<GridCoord, float>, 8> kNeighbors{{
    {GridCoord{-1, -1}, 1.41421356f},
    {GridCoord{0, -1}, 1.0f},
    {GridCoord{1, -1}, 1.41421356f},
    {GridCoord{-1, 0}, 1.0f},
    {GridCoord{1, 0}, 1.0f},
    {GridCoord{-1, 1}, 1.41421356f},
    {GridCoord{0, 1}, 1.0f},
    {GridCoord{1, 1}, 1.41421356f},
}};

}  // namespace

NavGrid::NavGrid(const Vec2& top_left, const Vec2& bottom_right, float node_spacing,
                  const std::vector<physics::Obstacle>& obstacles)
    : top_left_(top_left), node_spacing_(node_spacing) {
    width_ = static_cast<int>((bottom_right.x - top_left.x) / node_spacing_);
    height_ = static_cast<int>((bottom_right.y - top_left.y) / node_spacing_);
    blocked_.assign(static_cast<std::size_t>(width_) * static_cast<std::size_t>(height_), false);

    for (int gy = 0; gy < height_; ++gy) {
        for (int gx = 0; gx < width_; ++gx) {
            const Vec2 world = GridToWorld({gx, gy});
            bool blocked = false;
            for (const auto& obstacle : obstacles) {
                if (physics::PointInPolygon(obstacle.polygon, world)) {
                    blocked = true;
                    break;
                }
            }
            blocked_[Index({gx, gy})] = blocked;
        }
    }
}

GridCoord NavGrid::WorldToGrid(const Vec2& world) const {
    return GridCoord{static_cast<int>(std::floor((world.x - top_left_.x) / node_spacing_)),
                      static_cast<int>(std::floor((world.y - top_left_.y) / node_spacing_))};
}

Vec2 NavGrid::GridToWorld(const GridCoord& coord) const {
    return Vec2{top_left_.x + static_cast<float>(coord.x) * node_spacing_ + node_spacing_ * 0.5f,
                top_left_.y + static_cast<float>(coord.y) * node_spacing_ + node_spacing_ * 0.5f};
}

bool NavGrid::IsValid(const GridCoord& coord) const {
    if (coord.x < 0 || coord.x >= width_ || coord.y < 0 || coord.y >= height_) {
        return false;
    }
    return !blocked_[Index(coord)];
}

std::size_t NavGrid::Index(const GridCoord& coord) const {
    return static_cast<std::size_t>(coord.y) * static_cast<std::size_t>(width_) + static_cast<std::size_t>(coord.x);
}

std::optional<GridCoord> NavGrid::NearestValid(const Vec2& world) const {
    const GridCoord base = WorldToGrid(world);
    if (IsValid(base)) {
        return base;
    }
    constexpr int kMaxSearchRadius = 20;
    for (int radius = 1; radius <= kMaxSearchRadius; ++radius) {
        for (int dy = -radius; dy <= radius; ++dy) {
            for (int dx = -radius; dx <= radius; ++dx) {
                if (std::max(std::abs(dx), std::abs(dy)) != radius) {
                    continue;  // Only the ring perimeter at this radius - already checked smaller rings.
                }
                const GridCoord candidate{base.x + dx, base.y + dy};
                if (IsValid(candidate)) {
                    return candidate;
                }
            }
        }
    }
    return std::nullopt;
}

std::optional<std::vector<Vec2>> NavGrid::FindPath(const Vec2& from, const Vec2& to) const {
    const auto start = NearestValid(from);
    const auto goal = NearestValid(to);
    if (!start || !goal) {
        return std::nullopt;
    }
    if (*start == *goal) {
        return std::vector<Vec2>{GridToWorld(*goal)};
    }

    struct OpenEntry {
        float f_cost;
        GridCoord coord;
    };
    struct Compare {
        bool operator()(const OpenEntry& a, const OpenEntry& b) const { return a.f_cost > b.f_cost; }
    };

    std::priority_queue<OpenEntry, std::vector<OpenEntry>, Compare> open;
    std::unordered_map<GridCoord, float, GridCoordHash> g_cost;
    std::unordered_map<GridCoord, GridCoord, GridCoordHash> came_from;

    g_cost[*start] = 0.0f;
    open.push({0.0f, *start});

    const Vec2 goal_world = GridToWorld(*goal);

    while (!open.empty()) {
        const GridCoord current = open.top().coord;
        open.pop();

        if (current == *goal) {
            std::vector<Vec2> path;
            GridCoord walker = current;
            path.push_back(GridToWorld(walker));
            while (came_from.contains(walker)) {
                walker = came_from.at(walker);
                path.push_back(GridToWorld(walker));
            }
            std::reverse(path.begin(), path.end());
            return path;
        }

        for (const auto& [offset, cost] : kNeighbors) {
            const GridCoord neighbor{current.x + offset.x, current.y + offset.y};
            if (!IsValid(neighbor)) {
                continue;
            }
            if (offset.x != 0 && offset.y != 0) {
                // Disallow corner-cutting: both flanking orthogonal cells must also be open.
                if (!IsValid(GridCoord{current.x + offset.x, current.y}) ||
                    !IsValid(GridCoord{current.x, current.y + offset.y})) {
                    continue;
                }
            }

            const float tentative_g = g_cost.at(current) + cost;
            const auto it = g_cost.find(neighbor);
            if (it == g_cost.end() || tentative_g < it->second) {
                g_cost[neighbor] = tentative_g;
                const float heuristic = (goal_world - GridToWorld(neighbor)).Length();
                open.push({tentative_g + heuristic, neighbor});
                came_from[neighbor] = current;
            }
        }
    }
    return std::nullopt;
}

std::vector<Vec2> NavGrid::FindValidNodesNear(const Vec2& center, float radius) const {
    std::vector<Vec2> result;
    const GridCoord center_coord = WorldToGrid(center);
    const auto cell_radius = static_cast<int>(std::ceil(radius / node_spacing_)) + 1;

    for (int dy = -cell_radius; dy <= cell_radius; ++dy) {
        for (int dx = -cell_radius; dx <= cell_radius; ++dx) {
            const GridCoord candidate{center_coord.x + dx, center_coord.y + dy};
            if (!IsValid(candidate)) {
                continue;
            }
            const Vec2 world = GridToWorld(candidate);
            if ((world - center).LengthSquared() <= radius * radius) {
                result.push_back(world);
            }
        }
    }
    return result;
}

}  // namespace tank::ai
