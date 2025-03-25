import map_grid
import utils.helper_functions as hf

# Load the polygons and units (assuming this function is correct)
polygons, units = hf.load_map_data(r"map_files\map_test1.txt")

top_left = polygons[0][3]
print(top_left)

# Call get_mapgrid_dict on the instance
grid_dict = map_grid.get_mapgrid_dict(polygons, 50)

path = map_grid.find_path(grid_dict, (0,0), (15,11))


print(path)


def left_turn(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]) >= 0







print(left_turn((0,0), (5,0), (1,-1)))
