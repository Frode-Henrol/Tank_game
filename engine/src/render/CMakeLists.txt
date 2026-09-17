add_library(tank_render STATIC
    src/window.cpp
    src/texture_cache.cpp
    src/sprite_renderer.cpp
    src/polygon_renderer.cpp
)
add_library(tank::render ALIAS tank_render)

target_include_directories(tank_render PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_render PUBLIC tank::ecs SDL3::SDL3 SDL3_image::SDL3_image SDL3_ttf::SDL3_ttf imgui::imgui)
