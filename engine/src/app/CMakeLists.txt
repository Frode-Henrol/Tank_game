add_executable(tank_game
    src/main.cpp
)

target_link_libraries(tank_game PRIVATE
    tank::core
    tank::render
    tank::sim
    tank::ai
    tank::content
    tank::audio
    tank::ui
    tank::ecs
    SDL3::SDL3
)

# Points the M0 smoke test at the existing Python project's asset folders (tankgame/units, etc.)
# so it can reuse real sprites without any asset conversion step.
target_compile_definitions(tank_game PRIVATE ASSET_ROOT="${CMAKE_SOURCE_DIR}/../tankgame")
