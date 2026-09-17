#pragma once

#include <optional>
#include <string>
#include <vector>

#include "tank/ecs/vec2.hpp"
#include "tank/physics/obstacle.hpp"

namespace tank::content {

using tank::ecs::Vec2;

struct UnitSpawn {
    Vec2 position{};
    float angle_deg = 0.0f;
    int type_code = 0;  // index into tank_mappings (see units.json loader, added in M3)
    int team = 0;
};

struct MapData {
    physics::Polygon border;  // first Polygons: entry - bounding rect, not a collidable obstacle
    std::vector<physics::Obstacle> obstacles;
    std::vector<UnitSpawn> spawns;
    int node_spacing = 50;
};

// Parses the original's map text format unchanged (Polygons:/Units:/Nodespacing: sections,
// Python-tuple-literal-style lines) so every existing map_files/*.txt level and map_maker.py
// keep working with zero conversion. Returns std::nullopt if the file can't be opened;
// individual malformed lines are logged and skipped rather than failing the whole load
// (matching the original's tolerance).
std::optional<MapData> LoadMap(const std::string& path);

}  // namespace tank::content
