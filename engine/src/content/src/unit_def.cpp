#include "tank/content/unit_def.hpp"

#include <fstream>
#include <iostream>
#include <optional>

#include <nlohmann/json.hpp>

namespace tank::content {

namespace {

using Json = nlohmann::json;

std::optional<Json> LoadJsonFile(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        std::cerr << "LoadJsonFile: could not open '" << path << "'\n";
        return std::nullopt;
    }
    try {
        Json parsed;
        file >> parsed;
        return parsed;
    } catch (const Json::parse_error& error) {
        std::cerr << "LoadJsonFile: failed to parse '" << path << "': " << error.what() << "\n";
        return std::nullopt;
    }
}

AIPersonalityDef ParsePersonality(const Json& entry) {
    AIPersonalityDef def;
    def.patrol_radius = entry.value("patrol_radius", def.patrol_radius);
    def.dist_leave_patrol = entry.value("dist_leave_patrol", def.dist_leave_patrol);
    def.dist_leave_defend = entry.value("dist_leave_defend", def.dist_leave_defend);
    def.dist_leave_attack = entry.value("dist_leave_attack", def.dist_leave_attack);
    def.can_dodge_proj = entry.value("can_dodge_proj", def.can_dodge_proj);
    def.dist_start_dodge = entry.value("dist_start_dodge", def.dist_start_dodge);
    def.proj_dodge_cooldown_val = entry.value("proj_dodge_cooldown_val", def.proj_dodge_cooldown_val);
    def.aiming_angle = entry.value("aiming_angle", def.aiming_angle);
    def.perfect_aim = entry.value("perfect_aim", def.perfect_aim);
    def.predictive_targeting = entry.value("predictive_targeting", def.predictive_targeting);
    def.predictive_targeting_chance = entry.value("predictive_targeting_chance", def.predictive_targeting_chance);
    def.shoot_threshold = entry.value("shoot_threshold", def.shoot_threshold);
    def.safe_threshold = entry.value("safe_threshold", def.safe_threshold);
    def.defend_time = entry.value("defend_time", def.defend_time);
    def.mine_chance = entry.value("mine_chance", def.mine_chance);
    def.mine_min_distance = entry.value("mine_min_distance", def.mine_min_distance);
    def.random_mines = entry.value("random_mines", def.random_mines);
    def.avoid_mine_dist = entry.value("avoid_mine_dist", def.avoid_mine_dist);
    return def;
}

UnitDef ParseUnitDef(const Json& entry) {
    UnitDef def;
    def.tank_speed_modifier = entry.value("tank_speed_modifier", def.tank_speed_modifier);
    def.projectile_speed_modifier = entry.value("projectile_speed_modifier", def.projectile_speed_modifier);
    def.firerate = entry.value("firerate", def.firerate);
    def.bounch_limit = entry.value("bounch_limit", def.bounch_limit);
    def.mine_limit = entry.value("mine_limit", def.mine_limit);
    def.projectile_limit = entry.value("projectile_limit", def.projectile_limit);
    def.ai_personality = entry.value("ai_personality", def.ai_personality);
    def.use_mag_reload_logic = entry.value("use_mag_reload_logic", def.use_mag_reload_logic);
    def.mag_size = entry.value("mag_size", def.mag_size);
    def.reload_time = entry.value("reload_time", def.reload_time);
    return def;
}

}  // namespace

UnitDefTable LoadUnitDefs(const std::string& path) {
    UnitDefTable table;
    const auto parsed = LoadJsonFile(path);
    if (!parsed) {
        return table;
    }
    for (auto it = parsed->begin(); it != parsed->end(); ++it) {
        table.emplace(it.key(), ParseUnitDef(it.value()));
    }
    return table;
}

AIPersonalityTable LoadAIPersonalities(const std::string& path) {
    AIPersonalityTable table;
    const auto parsed = LoadJsonFile(path);
    if (!parsed) {
        return table;
    }
    for (auto it = parsed->begin(); it != parsed->end(); ++it) {
        table.emplace(it.key(), ParsePersonality(it.value()));
    }
    return table;
}

const std::string& UnitTypeCodeToName(int type_code) {
    static const std::unordered_map<int, std::string> kMapping = {
        {0, "player1_tank"},  {1, "brown_tank"},    {2, "ash_tank"},      {3, "marine_tank"},  {4, "yellow_tank"},
        {5, "pink_tank"},     {6, "green_tank"},    {7, "violet_tank"},   {8, "white_tank"},   {9, "black_tank"},
        {10, "zblue_tank"},   {11, "zbrown_tank"},  {12, "zash_tank"},    {13, "zmarine_tank"}, {14, "zyellow_tank"},
        {15, "zpink_tank"},   {16, "zgreen_tank"},  {17, "zviolet_tank"}, {18, "zwhite_tank"},  {19, "zblack_tank"},
        {20, "player2_tank"}, {21, "player3_tank"},
    };
    static const std::string kFallback = "player1_tank";
    const auto it = kMapping.find(type_code);
    return it != kMapping.end() ? it->second : kFallback;
}

}  // namespace tank::content
