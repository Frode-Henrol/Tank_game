#pragma once

#include <string>

#include <entt/entity/registry.hpp>

#include "tank/content/unit_def.hpp"
#include "tank/ecs/vec2.hpp"

namespace tank::content {

using tank::ecs::Vec2;

struct SpawnParams {
    Vec2 position;
    float heading_deg = 0.0f;
    int team = 0;
    int type_code = 0;  // map-file unit type code; resolved to a name via UnitTypeCodeToName
};

// The architecture plan's "entity factory": composes an entity's full component set from a
// UnitDef (+, for a non-player unit, an AIPersonality) - a new vehicle/infantry type becomes
// authoring data here, not writing a new C++ type. `asset_root` is prefixed onto the sprite's
// texture path; it is never opened here (this module has no SDL dependency - actually loading
// the texture is the render module's job, triggered later by whatever reads the Sprite
// component).
[[nodiscard]] entt::entity SpawnUnit(entt::registry& registry, const UnitDefTable& unit_defs,
                                       const AIPersonalityTable& personalities, const SpawnParams& params,
                                       const std::string& asset_root,
                                       const std::string& selected_player_loadout = "player_classic");

}  // namespace tank::content
