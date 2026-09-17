# Map-file and UnitDef/AIPersonality JSON parsing + the entity factory ("spawn from UnitDef").
# No SDL dependency - this module only ever produces data (positions, stats, texture-id
# strings); actually loading a texture/sound from a texture-id is the render/audio modules'
# job. Full map parser + UnitDef schema land in M1/M3; this is a placeholder target for now.

add_library(tank_content STATIC
    src/placeholder.cpp
)
add_library(tank::content ALIAS tank_content)

target_include_directories(tank_content PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_content PUBLIC tank::ecs nlohmann_json::nlohmann_json)
