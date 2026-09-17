#include "tank/content/unit_factory.hpp"

#include "tank/ecs/gameplay_components.hpp"

namespace tank::content {

namespace ecs = tank::ecs;

namespace {

constexpr float kSpeedToPixelsPerSecond = 60.0f;  // matches the original's `speed = base*dt*60` normalization
constexpr float kTurnRateDegPerSec = 180.0f;      // no personality-driven equivalent in the original
constexpr float kCollisionHalfWidth = 20.0f;
constexpr float kCollisionHalfHeight = 24.0f;  // matches the 40x48 Sprite below, not a 40x40 square
constexpr float kMaxHealth = 1.0f;             // instant-kill weapons deal damage == max_health
constexpr float kFireRateToIntervalSec = 5.0f / 60.0f;  // matches the original's cannon_cooldown = firerate*5 (60Hz-ticks)
constexpr float kReloadTimeToSec = 1.0f / 60.0f;        // reload_time is already in 60Hz-normalized ticks

}  // namespace

entt::entity SpawnUnit(entt::registry& registry, const UnitDefTable& unit_defs, const AIPersonalityTable& personalities,
                        const SpawnParams& params, const std::string& asset_root,
                        const std::string& selected_player_loadout) {
    const std::string& mapped_name = UnitTypeCodeToName(params.type_code);
    const bool is_player = mapped_name.rfind("player", 0) == 0;
    const std::string& stats_key = is_player ? selected_player_loadout : mapped_name;

    const auto unit_def_it = unit_defs.find(stats_key);
    const UnitDef unit_def = unit_def_it != unit_defs.end() ? unit_def_it->second : UnitDef{};

    const auto entity = registry.create();
    registry.emplace<ecs::Transform>(entity, params.position, params.heading_deg);
    registry.emplace<ecs::PreviousPosition>(entity, params.position);
    registry.emplace<ecs::TrackedMovement>(entity, unit_def.tank_speed_modifier * kSpeedToPixelsPerSecond,
                                            kTurnRateDegPerSec);
    registry.emplace<ecs::CollisionShape>(entity, ecs::ColliderShape::Box, kCollisionHalfWidth, kCollisionHalfHeight);
    registry.emplace<ecs::Health>(entity, kMaxHealth, kMaxHealth, 1.0f);
    registry.emplace<ecs::Faction>(entity, params.team);
    registry.emplace<ecs::MovementIntent>(entity);
    registry.emplace<ecs::AimIntent>(entity, Vec2{params.position.x + 1.0f, params.position.y});
    registry.emplace<ecs::FireIntent>(entity);
    registry.emplace<ecs::MineIntent>(entity);
    registry.emplace<ecs::MineDeployer>(entity, 0.0f, unit_def.mine_limit, 0);

    ecs::WeaponDef weapon_def{};
    weapon_def.fire_interval_sec = unit_def.firerate * kFireRateToIntervalSec;
    weapon_def.projectile_speed = unit_def.projectile_speed_modifier * kSpeedToPixelsPerSecond;
    weapon_def.bounce_limit = unit_def.bounch_limit + 1;  // matches the original passing bounch_limit+1 into Tank()
    weapon_def.projectile_limit = unit_def.projectile_limit;
    weapon_def.magazine_size = unit_def.use_mag_reload_logic ? unit_def.mag_size : 0;
    weapon_def.reload_time_sec = unit_def.reload_time * kReloadTimeToSec;
    weapon_def.damage = kMaxHealth;
    registry.emplace<ecs::WeaponMounts>(
        entity, ecs::WeaponMounts{{ecs::WeaponState{weapon_def, 0.0f, weapon_def.magazine_size, 0.0f, false}}});

    const std::string texture = asset_root + "/units/images/" + mapped_name + ".png";
    registry.emplace<ecs::Sprite>(entity, ecs::Sprite{texture, 0.5f, 0.5f, 40.0f, 48.0f, 90.0f});

    if (is_player) {
        registry.emplace<ecs::PlayerControlled>(entity, 0);
        return entity;
    }

    registry.emplace<ecs::AIControlled>(entity);
    registry.emplace<ecs::NavAgent>(entity);

    const auto personality_it = personalities.find(unit_def.ai_personality);
    const AIPersonalityDef personality = personality_it != personalities.end() ? personality_it->second : AIPersonalityDef{};

    ecs::AIPersonalityTuning tuning{};
    tuning.patrol_radius = personality.patrol_radius;
    tuning.dist_leave_patrol = personality.dist_leave_patrol;
    tuning.dist_leave_defend = personality.dist_leave_defend;
    tuning.dist_leave_attack = personality.dist_leave_attack;
    tuning.can_dodge_proj = personality.can_dodge_proj;
    tuning.dist_start_dodge = personality.dist_start_dodge;
    tuning.dodge_cooldown_sec = personality.proj_dodge_cooldown_val / 60.0f;
    tuning.aiming_angle_deg = personality.aiming_angle;
    tuning.perfect_aim = personality.perfect_aim;
    tuning.predictive_targeting = personality.predictive_targeting;
    tuning.predictive_targeting_chance = personality.predictive_targeting_chance;
    tuning.shoot_threshold = personality.shoot_threshold;
    tuning.safe_threshold = personality.safe_threshold;
    tuning.defend_time_sec = personality.defend_time / 60.0f;
    tuning.mine_chance_per_sec = personality.mine_chance > 0.0f ? (60.0f / personality.mine_chance) : 0.0f;
    tuning.mine_min_distance = personality.mine_min_distance;
    tuning.random_mines = personality.random_mines;
    tuning.avoid_mine_dist = personality.avoid_mine_dist;
    registry.emplace<ecs::AIPersonalityTuning>(entity, tuning);

    return entity;
}

}  // namespace tank::content
