# Button/Textfield-equivalent widgets and menu screens, plus the optional Dear ImGui dev/debug
# overlay (imgui overlay itself still lands later in M4).

add_library(tank_ui STATIC
    src/font.cpp
    src/button.cpp
)
add_library(tank::ui ALIAS tank_ui)

target_include_directories(tank_ui PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_ui PUBLIC tank::ecs tank::core SDL3::SDL3 SDL3_ttf::SDL3_ttf imgui::imgui)
