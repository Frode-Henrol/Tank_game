#pragma once

#include <string>
#include <unordered_map>

// UnitDef/AIPersonality (M3): mirrors the original's units.json / ai.json on-disk schema
// exactly (same key names) so those files are ported unchanged, with zero data migration.

namespace tank::content {

// Mirrors one ai.json personality entry. Every field is optional in the JSON and falls back to
// these defaults, matching the original's `config.get(key, default)` pattern. See
// tank::ecs::AIPersonalityTuning (gameplay_components.hpp) for the resolved, unit-converted
// component this becomes at spawn time - that's what ai::BehaviorSystem actually reads.
struct AIPersonalityDef {
    float patrol_radius = 200.0f;
    float dist_leave_patrol = 500.0f;
    float dist_leave_defend = 800.0f;
    float dist_leave_attack = 200.0f;
    bool can_dodge_proj = true;
    float dist_start_dodge = 45.0f;
    float proj_dodge_cooldown_val = 30.0f;  // AI-ticks @ 60Hz in the original; converted /60 at spawn time
    float aiming_angle = 25.0f;
    bool perfect_aim = false;
    bool predictive_targeting = true;
    int predictive_targeting_chance = 50;  // percent
    float shoot_threshold = 10.0f;
    float safe_threshold = 50.0f;
    float defend_time = 600.0f;  // AI-ticks @ 60Hz in the original; converted /60 at spawn time
    float mine_chance = 10000.0f;
    float mine_min_distance = 250.0f;
    bool random_mines = false;
    float avoid_mine_dist = 300.0f;
};

// Mirrors one units.json entry (a player loadout or a fixed enemy type's stats).
struct UnitDef {
    float tank_speed_modifier = 1.0f;
    float projectile_speed_modifier = 1.0f;
    float firerate = 1.0f;
    int bounch_limit = 1;  // spelling matches the original JSON key exactly
    int mine_limit = 0;
    int projectile_limit = 5;
    std::string ai_personality = "player";  // "player" for a human-controlled loadout, else an ai.json key
    bool use_mag_reload_logic = false;
    int mag_size = 5;
    float reload_time = 90.0f;
};

using UnitDefTable = std::unordered_map<std::string, UnitDef>;
using AIPersonalityTable = std::unordered_map<std::string, AIPersonalityDef>;

// Loads tankgame/units/units.json / ai.json unchanged. Returns an empty table (logging to
// stderr) if the file can't be opened or parsed - callers fall back to UnitDef{}/
// AIPersonalityDef{} defaults for any key not found, the same tolerance the original has.
[[nodiscard]] UnitDefTable LoadUnitDefs(const std::string& path);
[[nodiscard]] AIPersonalityTable LoadAIPersonalities(const std::string& path);

// The original's tank_mappings dict (tankgame.py's load_map()): a map file unit spawn's numeric
// type code -> the units.json/texture-file key that names its stats and sprite. 0/20/21 are all
// player slots (20/21 only matter for multiplayer, dropped from this port, but the numbering is
// kept stable since existing map files use it); everything else is a fixed enemy type.
// Hardcoded here because the original hardcodes it too - there's nothing to gain by moving a
// fixed, never-edited table into a data file.
[[nodiscard]] const std::string& UnitTypeCodeToName(int type_code);

}  // namespace tank::content
