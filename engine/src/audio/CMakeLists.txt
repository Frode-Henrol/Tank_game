# SDL3_mixer wrapper: channel-pool playback, random-variant-per-category sound selection
# (matches pygame.mixer's model from the original). Full implementation lands in M4; this is a
# placeholder target for now so the module boundary/dependency graph is fixed from M0 onward.

add_library(tank_audio STATIC
    src/placeholder.cpp
)
add_library(tank::audio ALIAS tank_audio)

target_include_directories(tank_audio PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_audio PUBLIC SDL3_mixer::SDL3_mixer)
