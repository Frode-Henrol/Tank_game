// Deterministic, headless integration test for the M1 simulation pipeline. Every tick uses an
// explicit fixed delta_time (no wall clock, no OS input, no SDL) so results are fully
// repeatable - this replaced trying to verify M1 by scripting synthetic keyboard/mouse input
// into the real windowed game, which proved unreliable to control precisely from outside the
// process.

#include <cmath>
#include <cstdio>
#include <string>
#include <unordered_map>
#include <utility>

#include <entt/entt.hpp>

#include "tank/content/map_loader.hpp"
#include "tank/ecs/gameplay_components.hpp"
#include "tank/physics/obstacle_world.hpp"
#include "tank/physics/oriented_box.hpp"
#include "tank/sim/collision_system.hpp"
#include "tank/sim/mine_system.hpp"
#include "tank/sim/movement_system.hpp"
#include "tank/sim/projectile_system.hpp"
#include "tank/sim/weapon_system.hpp"

namespace ecs = tank::ecs;
using tank::ecs::Vec2;

namespace {

int g_failures = 0;

bool Check(bool condition, const std::string& description) {
    if (condition) {
        std::printf("  [PASS] %s\n", description.c_str());
    } else {
        std::printf("  [FAIL] %s\n", description.c_str());
        ++g_failures;
    }
    return condition;
}

bool NearlyEqual(float a, float b, float epsilon) { return std::fabs(a - b) <= epsilon; }

void TestMapLoading() {
    std::printf("-- MapLoading --\n");
    const auto map = tank::content::LoadMap(std::string(ASSET_ROOT) + "/map_files/map_test1.txt");
    Check(map.has_value(), "map_test1.txt loads");
    if (!map) {
        return;
    }
    Check(map->border.size() == 4, "border has 4 corners");
    Check(map->obstacles.size() == 21, "21 non-border obstacles parsed");
    Check(map->spawns.size() == 9, "9 unit spawns parsed");
    Check(map->node_spacing == 50, "node_spacing parsed as 50");

    int standard_count = 0, destructible_count = 0;
    for (const auto& obstacle : map->obstacles) {
        if (obstacle.type == tank::physics::ObstacleType::Standard) {
            ++standard_count;
        } else if (obstacle.type == tank::physics::ObstacleType::Destructible) {
            ++destructible_count;
        }
    }
    Check(standard_count == 11, "11 standard obstacles");
    Check(destructible_count == 10, "10 destructible obstacles");
}

void TestMovement() {
    std::printf("-- Movement --\n");
    entt::registry registry;
    tank::sim::TrackedMovementSystem system;
    constexpr float dt = 1.0f / 100.0f;

    // Straight-line throttle.
    {
        const auto entity = registry.create();
        registry.emplace<ecs::Transform>(entity, Vec2{100.0f, 100.0f}, 0.0f);
        registry.emplace<ecs::TrackedMovement>(entity, 100.0f, 90.0f);
        registry.emplace<ecs::MovementIntent>(entity, ecs::MovementIntent{1.0f, 0.0f, false, 0.0f});

        for (int i = 0; i < 100; ++i) {
            system.Update(registry, dt);
        }
        const auto& transform = registry.get<ecs::Transform>(entity);
        Check(NearlyEqual(transform.position.x, 200.0f, 1.0f), "throttle=1 for 1s at 100px/s moves +100 on x");
        Check(NearlyEqual(transform.position.y, 100.0f, 1.0f), "y unchanged when heading=0");
    }

    // Turn axis.
    {
        const auto entity = registry.create();
        registry.emplace<ecs::Transform>(entity, Vec2{0.0f, 0.0f}, 0.0f);
        registry.emplace<ecs::TrackedMovement>(entity, 0.0f, 90.0f);
        registry.emplace<ecs::MovementIntent>(entity, ecs::MovementIntent{0.0f, 1.0f, false, 0.0f});

        for (int i = 0; i < 50; ++i) {
            system.Update(registry, dt);
        }
        const auto& transform = registry.get<ecs::Transform>(entity);
        Check(NearlyEqual(transform.heading_deg, 45.0f, 1.0f), "turn_axis=1 for 0.5s at 90deg/s rotates 45deg");
    }

    // Turn-towards, clamped by turn rate.
    {
        const auto entity = registry.create();
        registry.emplace<ecs::Transform>(entity, Vec2{0.0f, 0.0f}, 0.0f);
        registry.emplace<ecs::TrackedMovement>(entity, 0.0f, 90.0f);
        registry.emplace<ecs::MovementIntent>(entity, ecs::MovementIntent{0.0f, 0.0f, true, 170.0f});

        system.Update(registry, dt);
        const auto& transform = registry.get<ecs::Transform>(entity);
        Check(NearlyEqual(transform.heading_deg, 0.9f, 0.05f),
              "turn_towards is clamped to turn_rate*dt (0.9deg) in one tick, not snapped");
    }
}

void TestWallCollision() {
    std::printf("-- WallCollision --\n");
    entt::registry registry;
    const tank::physics::OrientedBoxCache box_cache;
    tank::physics::ObstacleWorld world;

    // Winding matches every real obstacle in the map files (top-left, top-right, bottom-right,
    // bottom-left - clockwise as drawn on screen), which is what makes EdgeNormals(...).second
    // reliably point outward.
    tank::physics::Obstacle box{{{100.0f, 100.0f}, {200.0f, 100.0f}, {200.0f, 200.0f}, {100.0f, 200.0f}},
                                 tank::physics::ObstacleType::Standard,
                                 false};
    world.SetObstacles({box});

    const auto entity = registry.create();
    registry.emplace<ecs::Transform>(entity, Vec2{150.0f, 250.0f}, 270.0f);  // below the box, heading up
    registry.emplace<ecs::PreviousPosition>(entity, Vec2{150.0f, 250.0f});
    registry.emplace<ecs::TrackedMovement>(entity, 200.0f, 0.0f);
    registry.emplace<ecs::CollisionShape>(entity, ecs::ColliderShape::Box, 20.0f, 20.0f);
    registry.emplace<ecs::MovementIntent>(entity, ecs::MovementIntent{1.0f, 0.0f, false, 0.0f});

    tank::sim::TrackedMovementSystem movement_system;
    tank::sim::WallCollisionSystem collision_system(box_cache);
    constexpr float dt = 1.0f / 100.0f;

    for (int i = 0; i < 300; ++i) {
        movement_system.Update(registry, dt);
        collision_system.Update(registry, world, dt);
    }

    const auto& transform = registry.get<ecs::Transform>(entity);
    Check(transform.position.y > 205.0f, "tank pushed back out of the wall, not tunneled through it (y=" +
                                              std::to_string(transform.position.y) + ")");
    Check(transform.position.y < 260.0f, "tank settles near the wall boundary, not stuck far away");
}

void TestTunnelPrevention() {
    std::printf("-- TunnelPrevention --\n");
    // Reported bug: at certain approach angles, a large-enough single-tick displacement can
    // carry a tank clean through a wall, because neither its pre-move nor post-move position
    // ever overlaps the wall in a same-tick snapshot test. Set up exactly that: a thin wall,
    // and one very fast diagonal tick whose start and end boxes both sit clear of the wall on
    // opposite sides, while the straight-line path between them passes right through it.
    entt::registry registry;
    const tank::physics::OrientedBoxCache box_cache;
    tank::physics::ObstacleWorld world;

    tank::physics::Obstacle wall{{{300.0f, 50.0f}, {310.0f, 50.0f}, {310.0f, 250.0f}, {300.0f, 250.0f}},
                                  tank::physics::ObstacleType::Standard,
                                  false};
    world.SetObstacles({wall});

    const auto entity = registry.create();
    registry.emplace<ecs::Transform>(entity, Vec2{250.0f, 100.0f}, 45.0f);  // diagonal approach, not axis-aligned
    registry.emplace<ecs::PreviousPosition>(entity, Vec2{250.0f, 100.0f});
    registry.emplace<ecs::TrackedMovement>(entity, 20000.0f, 0.0f);  // deliberately huge: ~200px this one tick
    registry.emplace<ecs::CollisionShape>(entity, ecs::ColliderShape::Box, 20.0f, 20.0f);
    registry.emplace<ecs::MovementIntent>(entity, ecs::MovementIntent{1.0f, 0.0f, false, 0.0f});

    tank::sim::TrackedMovementSystem movement_system;
    tank::sim::WallCollisionSystem collision_system(box_cache);
    constexpr float dt = 1.0f / 100.0f;

    movement_system.Update(registry, dt);
    const auto& after_move = registry.get<ecs::Transform>(entity);
    Check(after_move.position.x > 310.0f,
          "sanity check: the naive post-move position really is already past the wall (x=" +
              std::to_string(after_move.position.x) + ")");

    collision_system.Update(registry, world, dt);
    const auto& transform = registry.get<ecs::Transform>(entity);
    Check(transform.position.x < 300.0f,
          "swept collision catches the tunnel and reverts to before the wall, not left past it (x=" +
              std::to_string(transform.position.x) + ")");
}

void TestGlideAlongWall() {
    std::printf("-- GlideAlongWall --\n");
    // Reported from playtesting: tanks now "stick" to a wall instead of gliding along it like
    // the original. A tank driving into a wall at an angle should keep making progress along
    // the wall's surface (the original never reverts movement at all - collision response only
    // ever adds a push along the wall's normal on top of that tick's own move, so the tangential
    // component is never touched); only a head-on, purely-perpendicular approach should fully
    // stop. This drives at 45 degrees into a long wall for many ticks and checks the tank keeps
    // sliding down its length rather than freezing at first contact.
    entt::registry registry;
    const tank::physics::OrientedBoxCache box_cache;
    tank::physics::ObstacleWorld world;

    tank::physics::Obstacle wall{{{300.0f, 0.0f}, {310.0f, 0.0f}, {310.0f, 2000.0f}, {300.0f, 2000.0f}},
                                  tank::physics::ObstacleType::Standard,
                                  false};
    world.SetObstacles({wall});

    const auto entity = registry.create();
    registry.emplace<ecs::Transform>(entity, Vec2{250.0f, 100.0f}, 45.0f);
    registry.emplace<ecs::PreviousPosition>(entity, Vec2{250.0f, 100.0f});
    registry.emplace<ecs::TrackedMovement>(entity, 150.0f, 0.0f);  // realistic speed, not the tunnel test's extreme one
    registry.emplace<ecs::CollisionShape>(entity, ecs::ColliderShape::Box, 20.0f, 20.0f);
    registry.emplace<ecs::MovementIntent>(entity, ecs::MovementIntent{1.0f, 0.0f, false, 0.0f});

    tank::sim::TrackedMovementSystem movement_system;
    tank::sim::WallCollisionSystem collision_system(box_cache);
    constexpr float dt = 1.0f / 100.0f;

    for (int i = 0; i < 200; ++i) {
        movement_system.Update(registry, dt);
        collision_system.Update(registry, world, dt);
    }

    const auto& transform = registry.get<ecs::Transform>(entity);
    Check(transform.position.x < 300.0f, "tank stays outside the wall while sliding along it (x=" +
                                              std::to_string(transform.position.x) + ")");
    Check(transform.position.y > 100.0f + 50.0f,
          "tank keeps making progress down the wall's length instead of freezing at first contact (y=" +
              std::to_string(transform.position.y) + ", started at 100)");
}

void TestWeaponAndProjectile() {
    std::printf("-- WeaponAndProjectile --\n");
    entt::registry registry;
    tank::physics::ObstacleWorld world;  // empty - no walls, isolate projectile-vs-tank behavior

    const auto shooter = registry.create();
    registry.emplace<ecs::Transform>(shooter, Vec2{50.0f, 50.0f}, 0.0f);
    registry.emplace<ecs::Faction>(shooter, 1);
    registry.emplace<ecs::AimIntent>(shooter, Vec2{150.0f, 50.0f});
    registry.emplace<ecs::FireIntent>(shooter, ecs::FireIntent{0, true});
    ecs::WeaponDef def{};
    def.fire_interval_sec = 0.05f;
    def.projectile_speed = 300.0f;
    def.bounce_limit = 1;
    def.projectile_limit = 5;
    def.damage = 1.0f;
    registry.emplace<ecs::WeaponMounts>(shooter, ecs::WeaponMounts{{ecs::WeaponState{def, 0.0f, 0, 0.0f, false}}});

    const auto target = registry.create();
    registry.emplace<ecs::Transform>(target, Vec2{150.0f, 50.0f}, 0.0f);
    registry.emplace<ecs::CollisionShape>(target, ecs::ColliderShape::Box, 20.0f, 20.0f);
    registry.emplace<ecs::Health>(target, 1.0f, 1.0f, 1.0f);

    tank::sim::WeaponSystem weapon_system;
    tank::sim::ProjectileSystem projectile_system;
    constexpr float dt = 1.0f / 100.0f;

    weapon_system.Update(registry, dt);
    Check(registry.view<ecs::ProjectileState>().size() == 1, "firing spawns exactly one projectile");

    bool target_died = false;
    for (int i = 0; i < 50 && !target_died; ++i) {
        projectile_system.Update(registry, world, dt);
        if (registry.get<ecs::Health>(target).current <= 0.0f) {
            target_died = true;
        }
    }
    Check(target_died, "projectile travels from shooter to target and kills it");
    Check(registry.view<ecs::ProjectileState>().size() == 0, "projectile is destroyed on impact");

    // Per explicit product feedback: a dead tank's hitbox still physically blocks/absorbs a
    // shot - only its ability to take further damage/act is gone, not its collision presence.
    const auto shooter2 = registry.create();
    registry.emplace<ecs::Transform>(shooter2, Vec2{50.0f, 50.0f}, 0.0f);
    registry.emplace<ecs::Faction>(shooter2, 1);
    registry.emplace<ecs::AimIntent>(shooter2, Vec2{150.0f, 50.0f});
    registry.emplace<ecs::FireIntent>(shooter2, ecs::FireIntent{0, true});
    registry.emplace<ecs::WeaponMounts>(shooter2, ecs::WeaponMounts{{ecs::WeaponState{def, 0.0f, 0, 0.0f, false}}});

    weapon_system.Update(registry, dt);
    const float health_after_death = registry.get<ecs::Health>(target).current;
    bool second_shot_absorbed = false;
    for (int i = 0; i < 50 && !second_shot_absorbed; ++i) {
        projectile_system.Update(registry, world, dt);
        if (registry.view<ecs::ProjectileState>().size() == 0) {
            second_shot_absorbed = true;
        }
    }
    Check(second_shot_absorbed, "a dead tank's wreck still blocks/absorbs a later shot");
    Check(registry.get<ecs::Health>(target).current == health_after_death,
          "an already-dead tank takes no further damage from being hit again");
}

void TestHitRadiusCoversCorners() {
    std::printf("-- HitRadiusCoversCorners --\n");
    // Reported from playtesting: shots that visually clip a tank near its corner were whiffing.
    // Constructs a shot whose closest approach to the box's center is 25px along the exact
    // corner diagonal - inside the box's real corner-to-center reach (sqrt(20^2+20^2)=~28.3) but
    // farther than the old, too-small max(half_width,half_height)=20 radius - and checks it now
    // registers as a hit.
    entt::registry registry;
    tank::physics::ObstacleWorld world;  // empty - isolate the hit-radius math itself

    const Vec2 center{150.0f, 50.0f};
    const auto target = registry.create();
    registry.emplace<ecs::Transform>(target, center, 0.0f);
    registry.emplace<ecs::CollisionShape>(target, ecs::ColliderShape::Box, 20.0f, 20.0f);
    registry.emplace<ecs::Health>(target, 1.0f, 1.0f, 1.0f);

    constexpr float kInvSqrt2 = 0.70710678f;
    const Vec2 offset_dir{kInvSqrt2, kInvSqrt2};  // center -> corner direction
    const Vec2 line_dir{kInvSqrt2, -kInvSqrt2};   // perpendicular to offset_dir
    const Vec2 closest_point = center + offset_dir * 25.0f;
    const Vec2 old_pos = closest_point - line_dir * 200.0f;

    const auto projectile = registry.create();
    registry.emplace<ecs::Transform>(projectile, old_pos, 0.0f);
    registry.emplace<ecs::ProjectileState>(
        projectile, ecs::ProjectileState{entt::null, line_dir, old_pos, 40000.0f, 0, 1, 1.0f, 5.0f, 0.0f});

    tank::sim::ProjectileSystem projectile_system;
    projectile_system.Update(registry, world, 1.0f / 100.0f);

    Check(registry.get<ecs::Health>(target).current <= 0.0f,
          "a shot passing 25px from center along the corner diagonal - inside the box's real "
          "~28.3px corner reach, beyond the old too-small max(hw,hh)=20 radius - now hits");
}

// True only if `point` is at least `margin` px inside every side of `polygon`'s own bounding
// box - every obstacle in this game is an axis-aligned rectangle, so this is exact for the
// shapes actually in play. Deliberately not physics::PointInPolygon here: that function jitters
// its query point by ~0.03px to dodge ray-casting degeneracies, which is fine for gameplay but
// makes it unsuitable as a *precise* boundary test - a point that is genuinely still 0.01px
// outside a wall (i.e. correctly not yet collided) can register as "inside" purely from that
// jitter, which is a false positive for this test's purpose, not a real tunneling bug.
bool IsMeaningfullyInside(const tank::physics::Polygon& polygon, const Vec2& point, float margin) {
    if (polygon.empty()) {
        return false;
    }
    float min_x = polygon[0].x, max_x = polygon[0].x, min_y = polygon[0].y, max_y = polygon[0].y;
    for (const auto& corner : polygon) {
        min_x = std::min(min_x, corner.x);
        max_x = std::max(max_x, corner.x);
        min_y = std::min(min_y, corner.y);
        max_y = std::max(max_y, corner.y);
    }
    return point.x > min_x + margin && point.x < max_x - margin && point.y > min_y + margin && point.y < max_y - margin;
}

void TestNoTunnelingAcrossRealMap() {
    std::printf("-- NoTunnelingAcrossRealMap --\n");
    // Brute-force repro attempt for "shots pass through blocks", against the actual map file at
    // actual gameplay speed - rather than a single hand-picked geometric case, fire projectiles
    // from a grid of points across the whole map in many directions and check, every tick,
    // whether any of them ends up strictly inside an obstacle polygon (which a projectile should
    // never be able to do - it should always bounce/stop at the boundary first).
    const auto map = tank::content::LoadMap(std::string(ASSET_ROOT) + "/map_files/map_test1.txt");
    if (!Check(map.has_value(), "map_test1.txt loads for the tunneling sweep")) {
        return;
    }

    tank::physics::ObstacleWorld world;
    world.SetObstacles(map->obstacles);

    entt::registry registry;
    constexpr float kRealProjectileSpeed = 3.36f * 60.0f;  // matches player_classic in main.cpp
    std::unordered_map<entt::entity, std::pair<Vec2, int>> spawn_info;  // entity -> (start pos, angle_deg)
    int spawned = 0;
    for (float x = map->border[3].x + 25.0f; x < map->border[1].x; x += 50.0f) {
        for (float y = map->border[3].y + 25.0f; y < map->border[1].y; y += 50.0f) {
            const Vec2 pos{x, y};
            bool inside_obstacle = false;
            for (const auto& obstacle : map->obstacles) {
                if (tank::physics::PointInPolygon(obstacle.polygon, pos)) {
                    inside_obstacle = true;
                    break;
                }
            }
            if (inside_obstacle) {
                continue;  // Don't spawn a projectile starting inside a wall - not the scenario under test.
            }
            for (int angle_deg = 0; angle_deg < 360; angle_deg += 30) {
                const float rad = static_cast<float>(angle_deg) * 3.14159265f / 180.0f;
                const auto projectile = registry.create();
                registry.emplace<ecs::Transform>(projectile, pos, 0.0f);
                registry.emplace<ecs::ProjectileState>(
                    projectile, ecs::ProjectileState{entt::null, Vec2{std::cos(rad), std::sin(rad)}, pos,
                                                       kRealProjectileSpeed, 0, 2, 1.0f, 5.0f, 0.0f});
                spawn_info[projectile] = {pos, angle_deg};
                ++spawned;
            }
        }
    }

    tank::sim::ProjectileSystem projectile_system;
    constexpr float dt = 1.0f / 100.0f;
    int tunneled_count = 0;
    Vec2 first_tunnel_pos{};
    Vec2 first_tunnel_spawn_pos{};
    int first_tunnel_spawn_angle = 0;
    int first_tunnel_tick = -1;
    int first_tunnel_bounce_count = -1;

    for (int tick = 0; tick < 400; ++tick) {
        projectile_system.Update(registry, world, dt);
        for (auto entity : registry.view<ecs::Transform, ecs::ProjectileState>()) {
            const auto& transform = registry.get<ecs::Transform>(entity);
            for (const auto& obstacle : world.Obstacles()) {
                if (obstacle.destroyed) {
                    continue;
                }
                if (IsMeaningfullyInside(obstacle.polygon, transform.position, 1.0f)) {
                    if (tunneled_count == 0) {
                        first_tunnel_pos = transform.position;
                        const auto [spawn_pos, spawn_angle] = spawn_info.at(entity);
                        first_tunnel_spawn_pos = spawn_pos;
                        first_tunnel_spawn_angle = spawn_angle;
                        first_tunnel_tick = tick;
                        first_tunnel_bounce_count = registry.get<ecs::ProjectileState>(entity).bounce_count;
                    }
                    ++tunneled_count;
                }
            }
        }
        if (tunneled_count > 0) {
            break;
        }
    }

    if (!Check(tunneled_count == 0, "none of " + std::to_string(spawned) +
                                         " projectiles fired in a full sweep of directions across the real map "
                                         "end up inside an obstacle")) {
        std::printf(
            "    first offender: spawned at (%.1f, %.1f) angle=%d, tunneled at tick %d to (%.3f, %.3f), "
            "bounce_count=%d\n",
            first_tunnel_spawn_pos.x, first_tunnel_spawn_pos.y, first_tunnel_spawn_angle, first_tunnel_tick,
            first_tunnel_pos.x, first_tunnel_pos.y, first_tunnel_bounce_count);
    }
}

void TestProjectileWallBounce() {
    std::printf("-- ProjectileWallBounce --\n");
    // No existing test actually fires a projectile at a wall - TestWallCollision/
    // TestTunnelPrevention only cover *tank* vs wall (WallCollisionSystem). This is
    // ProjectileSystem's own wall bounce, exercised directly.
    entt::registry registry;
    tank::physics::ObstacleWorld world;

    tank::physics::Obstacle wall{{{300.0f, 50.0f}, {310.0f, 50.0f}, {310.0f, 250.0f}, {300.0f, 250.0f}},
                                  tank::physics::ObstacleType::Standard,
                                  false};
    world.SetObstacles({wall});

    const auto projectile = registry.create();
    registry.emplace<ecs::Transform>(projectile, Vec2{250.0f, 150.0f}, 0.0f);
    // Deliberately fast enough to cross the whole 10px-thick wall in a single tick (100px this
    // tick), mirroring the tank tunneling scenario - a swept test must catch this regardless of
    // speed, not just a slow, many-ticks approach.
    registry.emplace<ecs::ProjectileState>(
        projectile, ecs::ProjectileState{entt::null, Vec2{1.0f, 0.0f}, Vec2{250.0f, 150.0f}, 10000.0f, 0, 2, 1.0f, 5.0f, 0.0f});

    tank::sim::ProjectileSystem projectile_system;
    projectile_system.Update(registry, world, 1.0f / 100.0f);

    const auto& transform = registry.get<ecs::Transform>(projectile);
    const auto& state = registry.get<ecs::ProjectileState>(projectile);
    Check(state.bounce_count == 1, "a fast projectile crossing a wall in one tick still registers a bounce");
    Check(transform.position.x < 300.0f, "the projectile ends up before the wall, not tunneled past it (x=" +
                                              std::to_string(transform.position.x) + ")");
    Check(state.direction.x < 0.0f, "direction reflects off the wall's vertical face (x-component flips sign)");
}

void TestSegmentIntersectionPrecisionAtMapScale() {
    std::printf("-- SegmentIntersectionPrecisionAtMapScale --\n");
    // Root cause of "shots pass through blocks", isolated to the exact failing case found by
    // TestNoTunnelingAcrossRealMap: a vertical segment crossing a horizontal wall edge at
    // real map coordinates (~1300). The true intersection is exactly (1325, 600) - verified by
    // hand via Cramer's rule - but SegmentIntersection's old epsilon (1e-9f) was calibrated for
    // double precision; at `float` precision and this coordinate magnitude, the division's
    // rounding error routinely exceeds that tolerance, so a coordinate landing exactly on an
    // axis-aligned edge (i.e. almost every wall in this game) would compute a few ULPs off and
    // get rejected as "outside" the edge.
    const Vec2 old_pos{1325.0f, 600.808f};
    const Vec2 new_pos{1325.0f, 598.792f};
    const Vec2 wall_a{1350.0f, 600.0f};
    const Vec2 wall_b{1300.0f, 600.0f};

    const auto intersection = tank::physics::SegmentIntersection(old_pos, new_pos, wall_a, wall_b);
    Check(intersection.has_value(), "a vertical segment crossing a horizontal wall edge at map-scale "
                                     "coordinates (~1300) is detected, not lost to float rounding error");
    if (intersection) {
        Check(NearlyEqual(intersection->x, 1325.0f, 0.1f) && NearlyEqual(intersection->y, 600.0f, 0.1f),
              "the detected intersection point is where it should be (1325, 600)");
    }
}

void TestMine() {
    std::printf("-- Mine --\n");
    entt::registry registry;
    tank::physics::ObstacleWorld world;

    tank::physics::Obstacle destructible{{{140.0f, 140.0f}, {160.0f, 140.0f}, {160.0f, 160.0f}, {140.0f, 160.0f}},
                                           tank::physics::ObstacleType::Destructible,
                                           false};
    world.SetObstacles({destructible});

    const auto deployer = registry.create();
    registry.emplace<ecs::Transform>(deployer, Vec2{100.0f, 100.0f}, 0.0f);
    registry.emplace<ecs::Faction>(deployer, 1);
    registry.emplace<ecs::MineDeployer>(deployer, 0.0f, 4, 0);
    registry.emplace<ecs::MineIntent>(deployer, ecs::MineIntent{true});

    const auto victim = registry.create();
    registry.emplace<ecs::Transform>(victim, Vec2{120.0f, 100.0f}, 0.0f);
    registry.emplace<ecs::Faction>(victim, 2);
    registry.emplace<ecs::Health>(victim, 1.0f, 1.0f, 1.0f);

    tank::sim::MineSystem mine_system;
    constexpr float dt = 1.0f / 100.0f;

    mine_system.Update(registry, world, dt);
    Check(registry.view<ecs::MineState>().size() == 1, "deploying spawns exactly one mine");
    Check(registry.get<ecs::MineDeployer>(deployer).active_count == 1, "deployer's active_count is tracked");
    // Simulate releasing the deploy input (a single press, not held) so the cooldown/limit gate
    // isn't exercised here - continuous holding correctly laying more mines up to the limit is
    // the deployer's actual designed behavior, not something this single-mine lifecycle test is
    // checking.
    registry.get<ecs::MineIntent>(deployer).want_deploy = false;

    // Let the mine's life timer run out naturally (10s) so it arms and explodes without needing
    // to special-case the countdown fields from outside the system.
    bool exploded = false;
    bool destructible_removed = false;
    bool mine_cleaned_up = false;
    for (int i = 0; i < 1400 && !mine_cleaned_up; ++i) {
        mine_system.Update(registry, world, dt);
        if (!exploded && registry.view<ecs::MineState>().size() > 0) {
            const auto mine_entity = *registry.view<ecs::MineState>().begin();
            if (registry.get<ecs::MineState>(mine_entity).exploded) {
                exploded = true;
            }
        }
        if (!world.Obstacles().empty() && world.Obstacles()[0].destroyed) {
            destructible_removed = true;
        }
        if (registry.view<ecs::MineState>().size() == 0) {
            mine_cleaned_up = true;
        }
    }
    Check(exploded, "mine auto-arms and explodes after its life timer");
    Check(registry.get<ecs::Health>(victim).current <= 0.0f, "explosion kills a tank within radius");
    Check(destructible_removed, "explosion removes a nearby destructible obstacle");
    Check(mine_cleaned_up, "exploded mine is removed after its cleanup delay");
    Check(registry.get<ecs::MineDeployer>(deployer).active_count == 0, "deployer's active_count is released on cleanup");
}

}  // namespace

int main() {
    TestMapLoading();
    TestMovement();
    TestWallCollision();
    TestTunnelPrevention();
    TestGlideAlongWall();
    TestWeaponAndProjectile();
    TestHitRadiusCoversCorners();
    TestProjectileWallBounce();
    TestSegmentIntersectionPrecisionAtMapScale();
    TestNoTunnelingAcrossRealMap();
    TestMine();

    if (g_failures == 0) {
        std::printf("\nsim_smoke_test: ALL CHECKS PASSED\n");
        return 0;
    }
    std::printf("\nsim_smoke_test: %d CHECK(S) FAILED\n", g_failures);
    return 1;
}
