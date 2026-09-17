#include "tank/content/map_loader.hpp"

#include <cctype>
#include <fstream>
#include <iostream>
#include <sstream>

namespace tank::content {

namespace {

// Extracts every number (int or float, optionally negative) appearing in `line`, in order.
// The map format's data lines are always Python-tuple-literal-style ("(...)"/"[...]" sequences
// of plain numbers), so pulling out just the numbers - rather than writing a general literal
// parser - is sufficient and exactly matches the fixed grammar every existing level uses.
std::vector<double> ExtractNumbers(const std::string& line) {
    std::vector<double> numbers;
    std::size_t i = 0;
    while (i < line.size()) {
        const bool is_digit_start = std::isdigit(static_cast<unsigned char>(line[i])) != 0;
        const bool is_negative_start =
            line[i] == '-' && i + 1 < line.size() && std::isdigit(static_cast<unsigned char>(line[i + 1])) != 0;

        if (!is_digit_start && !is_negative_start) {
            ++i;
            continue;
        }

        const std::size_t start = i;
        ++i;
        while (i < line.size() && (std::isdigit(static_cast<unsigned char>(line[i])) != 0 || line[i] == '.')) {
            ++i;
        }
        try {
            numbers.push_back(std::stod(line.substr(start, i - start)));
        } catch (const std::exception&) {
            // Not a valid number after all (e.g. a lone '.') - skip it, matching the original's
            // per-line "log and continue" tolerance.
        }
    }
    return numbers;
}

std::string Trim(const std::string& s) {
    const auto begin = s.find_first_not_of(" \t\r\n");
    if (begin == std::string::npos) {
        return "";
    }
    const auto end = s.find_last_not_of(" \t\r\n");
    return s.substr(begin, end - begin + 1);
}

}  // namespace

std::optional<MapData> LoadMap(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        std::cerr << "LoadMap: could not open '" << path << "'\n";
        return std::nullopt;
    }

    enum class Section { None, Polygons, Units };
    Section section = Section::None;

    MapData data;
    bool border_set = false;

    std::string raw_line;
    while (std::getline(file, raw_line)) {
        const std::string line = Trim(raw_line);
        if (line.empty()) {
            continue;
        }

        if (line == "Mapname:") {
            section = Section::None;  // The next line (the map's filename) is intentionally
                                       // ignored, matching the original loader.
            continue;
        }
        if (line == "Polygons:") {
            section = Section::Polygons;
            continue;
        }
        if (line == "Units:") {
            section = Section::Units;
            continue;
        }
        if (line.rfind("Nodespacing:", 0) == 0) {
            const auto colon = line.find(':');
            try {
                data.node_spacing = std::stoi(Trim(line.substr(colon + 1)));
            } catch (const std::exception&) {
                std::cerr << "LoadMap: invalid Nodespacing value in '" << path << "'\n";
            }
            continue;
        }

        if (section == Section::Polygons) {
            const std::vector<double> numbers = ExtractNumbers(line);
            if (numbers.size() < 3 || numbers.size() % 2 != 1) {
                std::cerr << "LoadMap: malformed polygon line, skipping: " << line << "\n";
                continue;
            }
            const int type_code = static_cast<int>(numbers.back());

            physics::Polygon polygon;
            polygon.reserve((numbers.size() - 1) / 2);
            for (std::size_t i = 0; i + 1 < numbers.size() - 1; i += 2) {
                polygon.push_back(Vec2{static_cast<float>(numbers[i]), static_cast<float>(numbers[i + 1])});
            }

            if (!border_set) {
                // The first Polygons: entry is always the map's bounding rectangle - it's not a
                // collidable obstacle, just used for map sizing/background placement/pathfinding
                // grid bounds (matches the original popping it off polygon_list_no_border).
                data.border = std::move(polygon);
                border_set = true;
            } else {
                data.obstacles.push_back(physics::Obstacle{std::move(polygon),
                                                             static_cast<physics::ObstacleType>(type_code), false});
            }
        } else if (section == Section::Units) {
            const std::vector<double> numbers = ExtractNumbers(line);
            if (numbers.size() != 5) {
                std::cerr << "LoadMap: malformed unit line, skipping: " << line << "\n";
                continue;
            }
            UnitSpawn spawn;
            spawn.position = Vec2{static_cast<float>(numbers[0]), static_cast<float>(numbers[1])};
            spawn.angle_deg = static_cast<float>(numbers[2]);
            spawn.type_code = static_cast<int>(numbers[3]);
            spawn.team = static_cast<int>(numbers[4]);
            data.spawns.push_back(spawn);
        }
    }

    if (!border_set) {
        std::cerr << "LoadMap: '" << path << "' has no border polygon\n";
        return std::nullopt;
    }

    return data;
}

}  // namespace tank::content
