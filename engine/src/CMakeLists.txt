# Dependency direction (enforced by which libraries below are linked, not just convention):
#
#   ecs       <- everything (just component/type definitions, header-only, no logic)
#   physics   <- ecs                          (pure math + spatial queries, NO SDL)
#   ai        <- ecs, physics                 (behavior/targeting/pathfinding, NO SDL - see ai/CMakeLists.txt)
#   sim       <- ecs, physics                 (movement/weapon/projectile/mine/damage systems, NO SDL)
#   content   <- ecs                          (map/JSON parsing + entity factory, NO SDL)
#   render    <- ecs, SDL3, SDL3_image, SDL3_ttf, imgui
#   audio     <- SDL3_mixer
#   ui        <- ecs, SDL3, SDL3_ttf, imgui, render
#   core      <- ecs, SDL3                     (App shell, window, fixed-timestep loop, State enum)
#   app       <- everything                   (wires it all together into the game executable)

add_subdirectory(ecs)
add_subdirectory(physics)
add_subdirectory(ai)
add_subdirectory(sim)
add_subdirectory(content)
add_subdirectory(render)
add_subdirectory(audio)
add_subdirectory(ui)
add_subdirectory(core)
add_subdirectory(app)
