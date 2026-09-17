# Button/Textfield-equivalent widgets and menu screens, plus the optional Dear ImGui dev/debug
# overlay. Full implementation lands in M4; this is a placeholder target for now so the module
# boundary/dependency graph is fixed from M0 onward.

add_library(tank_ui STATIC
    src/placeholder.cpp
)
add_library(tank::ui ALIAS tank_ui)

target_include_directories(tank_ui PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_ui PUBLIC tank::ecs SDL3::SDL3 SDL3_ttf::SDL3_ttf imgui::imgui)
