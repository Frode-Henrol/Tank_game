# Pure 2D math + spatial queries. Deliberately has NO dependency on SDL3 (or any rendering/
# audio/input library): both `sim` and `ai` depend on `physics`, and if physics linked SDL,
# that dependency would leak into `ai` transitively - defeating the point of keeping ai
# SDL-free. See ai/CMakeLists.txt for the enforced boundary this protects.

add_library(tank_physics STATIC
    src/geometry.cpp
    src/oriented_box.cpp
    src/spatial_hash_grid.cpp
    src/obstacle_world.cpp
)
add_library(tank::physics ALIAS tank_physics)

target_include_directories(tank_physics PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_physics PUBLIC tank::ecs)
