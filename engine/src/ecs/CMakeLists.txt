add_library(tank_ecs INTERFACE)
add_library(tank::ecs ALIAS tank_ecs)

target_include_directories(tank_ecs INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(tank_ecs INTERFACE EnTT::EnTT)
target_compile_features(tank_ecs INTERFACE cxx_std_20)
