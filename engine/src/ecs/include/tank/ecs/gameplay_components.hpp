#pragma once

// Component schema shared by every module. This header (plus vec2.hpp) is the entire surface
// the `ai` module is allowed to depend on from the rest of the engine, together with the
// world_query interface in the ai module itself - see engine/src/ai/CMakeLists.txt for how
// that boundary is enforced at the build-system level, not just by convention.
//
// Design rule: a unit is *never* a class. It is an entt::entity plus whichever of these
// components apply. Adding a new vehicle/infantry archetype means composing a new set of
// components (usually via a UnitDef in the content module), not writing a new C++ type.

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include <entt/entity/entity.hpp>

#include "tank/ecs/vec2.hpp"

namespace tank::ecs {

// ---- Spatial ----

struct Transform {
    Vec2 position{};
    float heading_deg = 0.0f;  // hull heading; 0 = +x axis, matches atan2(dy, dx) convention
};

// Position at the start of the current tick, before movement is applied. Written by the
// movement system for any entity that has it; consumed by WallCollisionSystem to do a *swept*
// test (old position -> new position) rather than only checking the box's final resting spot -
// a discrete "check only where I ended up" test can let a fast-enough or steep-enough approach
// slip through a wall between two samples without any single-frame overlap ever being detected.
struct PreviousPosition {
    Vec2 position{};
};

// ---- Movement ----
// One component type per locomotion "kind" so MovementSystem stays a `view<Transform, Kind,
// MovementIntent>` per kind rather than a branch in one god-system. A future infantry archetype
// adds a sibling `HolonomicMovement` (free 2D movement) + its own system, not a branch here.

struct TrackedMovement {
    float max_speed = 0.0f;      // world units/sec at full throttle; forward/back only, no strafe
    float turn_rate_deg = 0.0f;  // max hull turn rate, degrees/sec
};

// Desired motion for this tick. Written by exactly one of PlayerInputSystem / the ai module for
// any given entity, and consumed generically by the movement system for that entity's movement
// component - neither producer needs to know or care which one wrote it.
struct MovementIntent {
    float throttle = 0.0f;   // -1 (full reverse) .. 1 (full forward)
    float turn_axis = 0.0f;  // -1 (full left) .. 1 (full right); classic direct-rotate scheme
    // Alternate "directional" control scheme (rotate towards an absolute heading instead of a
    // raw turn axis) - set has_turn_target and MovementSystem uses turn_towards_deg instead of
    // turn_axis for this tick.
    bool has_turn_target = false;
    float turn_towards_deg = 0.0f;
};

// ---- Collision ----
// "Can I be walked/driven into" footprint. Deliberately not named Hitbox: a future Hurtbox
// (the region that can be *shot*, which may differ from the collision footprint - e.g.
// infantry) is a natural sibling component, not a rename of this one.

enum class ColliderShape : std::uint8_t {
    Box,
};

struct CollisionShape {
    ColliderShape shape = ColliderShape::Box;
    float half_width = 0.0f;
    float half_height = 0.0f;
};

// ---- Combat ----

struct Health {
    float current = 1.0f;
    float max = 1.0f;
    // Reserved for a future armor/resistance model (e.g. per damage-type multiplier). Unused
    // until then; kept now so adding it later isn't a schema migration.
    float damage_multiplier = 1.0f;
};

enum class ProjectileBehavior : std::uint8_t {
    Ballistic,  // straight line, reflects off walls up to bounce_limit (today's only behavior)
};

struct WeaponDef {
    float fire_interval_sec = 0.5f;
    float projectile_speed = 1.0f;
    int bounce_limit = 1;
    int projectile_limit = 5;  // max concurrently-alive projectiles fired from this weapon
    int magazine_size = 0;     // 0 = no magazine (limited only by projectile_limit/cooldown)
    float reload_time_sec = 0.0f;
    float damage = 1.0f;
    ProjectileBehavior behavior = ProjectileBehavior::Ballistic;
};

struct WeaponState {
    WeaponDef def;
    float cooldown_sec = 0.0f;
    int magazine_ammo = 0;
    float reload_timer_sec = 0.0f;
    bool reloading = false;
};

// A unit can carry more than one weapon (main cannon + a future secondary/coax, etc.).
struct WeaponMounts {
    std::vector<WeaponState> weapons;
};

// Mines are deployed, not aimed/fired through a turret, so they get their own component
// rather than living inside WeaponMounts.
struct MineDeployer {
    float cooldown_sec = 0.0f;
    int limit = 0;
    int active_count = 0;
};

// Per-instance projectile state. The "stats" (speed, bounce limit, damage) are copied in from
// the firing WeaponDef at spawn time - this is just the bookkeeping that changes over the
// projectile's lifetime.
struct ProjectileState {
    entt::entity owner = entt::null;
    Vec2 direction{1.0f, 0.0f};
    Vec2 spawn_position{};  // frozen at fire time; used by the AI's directional-cone dodge filter
    float speed = 1.0f;
    int bounce_count = 0;
    int bounce_limit = 1;
    float damage = 1.0f;
    float lifespan_sec = 5.0f;
    float spawn_immunity_sec = 0.0f;  // brief self-hit immunity right after firing
};

// Mine runtime state - deployed entity, not carried by the deploying unit.
struct MineState {
    entt::entity owner = entt::null;
    int team = 0;
    float explode_radius = 100.0f;
    float life_timer_sec = 10.0f;      // auto-arms once this reaches 0, even if never triggered
    float countdown_timer_sec = 2.0f;  // once armed, explodes when this reaches 0
    bool countdown_started = false;
    bool exploded = false;
    float cleanup_delay_sec = 0.5f;  // how long an exploded mine lingers before removal
};

// Aim/fire intent for this tick - same producer/consumer split as MovementIntent above.
struct AimIntent {
    Vec2 target{};
};

struct FireIntent {
    std::size_t weapon_slot = 0;
    bool want_fire = false;
};

struct MineIntent {
    bool want_deploy = false;
};

// ---- Teams ----

struct Faction {
    int team = 0;
};

// ---- Navigation ----
// Pathfinding state, kept separate from AIControlled below: a future player-issued "move to
// point" order should be able to drive this without dragging in the whole behavior FSM.

struct NavAgent {
    std::vector<Vec2> path;  // remaining waypoints in travel order; front = next waypoint
    std::size_t path_index = 0;
    float repath_timer_sec = 0.0f;
};

// ---- AI ----
// Scratch data owned entirely by the ai module - core sim and rendering never read or write
// this; they only ever see the Intent components above. See engine/src/ai/CMakeLists.txt for
// how this boundary is enforced, not just documented.

enum class BehaviorState : std::uint8_t {
    Idle,
    Patrolling,
    Defending,
    Attacking,
    Wander,
    Dodge,
};

struct AIControlled {
    int personality_id = -1;
    BehaviorState state = BehaviorState::Idle;
    entt::entity targeted_unit = entt::null;
    float state_timer_sec = 0.0f;
    float dodge_cooldown_sec = 0.0f;
    Vec2 spawn_position{};  // captured once on the Idle->Patrolling transition; patrol anchor

    // Aiming-inaccuracy cone (M2b): a persisted random angular offset from the true/lead-
    // corrected aim direction, re-rolled on a timer rather than every tick - approximates the
    // original's "hold the wander offset until the turret catches up to it" cadence without
    // this port modeling an independent turret-rotation-rate/lag system (out of scope; aiming
    // is instantaneous here, only its target direction is jittered).
    float aim_jitter_deg = 0.0f;
    float aim_jitter_timer_sec = 0.0f;
};

// Tag: exactly one of PlayerControlled / AIControlled is present on any unit that can act.
struct PlayerControlled {
    int player_index = 0;
};

// ---- Rendering ----

struct Sprite {
    std::string texture_id;
    float pivot_x = 0.5f;
    float pivot_y = 0.5f;
    float width = 0.0f;
    float height = 0.0f;
    float rotation_offset_deg = 0.0f;
};

}  // namespace tank::ecs
