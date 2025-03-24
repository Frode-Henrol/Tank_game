import map_grid
import utils.helper_functions as hf

# Load the polygons and units (assuming this function is correct)
polygons, units = hf.load_map_data(r"map_files\map_test1.txt")


# Call get_mapgrid_dict on the instance
print(map_grid.get_mapgrid_dict(polygons, 50))
