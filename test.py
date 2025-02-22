import ast  # For safely evaluating the string representation of the data

def load_map_data(map_name):
    """Load the map and polygons from the text file."""
    map_borders = []
    polygons = []

    try:
        with open(map_name, "r") as f:
            lines = f.readlines()

            # Read map borders (first line after the name)
            if lines:
                map_borders_line = lines[1].strip()  # Map borders are on the second line
                map_borders = ast.literal_eval(map_borders_line)

            # Read the polygons
            for line in lines[2:]:  # The rest are polygons
                polygon_points = ast.literal_eval(line.strip())
                polygons.append(polygon_points)

    except Exception as e:
        print(f"Error loading map data: {e}")

    return map_borders, polygons

map_name = r"map_files\map_test1.txt"
test = load_map_data(map_name)

print(test)

