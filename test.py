
import ast  

def load_map_data(map_name: str) -> tuple[list,list,int]:
    """Load the map and polygons/units from the text file. 
    Returns: (polygons, units, node_spacing)
    """
    polygons = []
    units = []
    node_spacing = None  # Default in case it's not found

    try:
        with open(map_name, "r") as f:
            lines = f.readlines()

            current_section = None
            for line in lines:
                line = line.strip()

                if not line:
                    continue
                
                # Identify section headers
                if line == "Polygons:":
                    current_section = "polygons"
                    continue
                elif line == "Units:":
                    current_section = "units"
                    continue
                elif line.startswith("Nodespacing:"):
                    try:
                        node_spacing = int(line.split(":")[1].strip())
                    except ValueError:
                        print("Warning: Invalid node spacing value.")
                    continue
                
                # Parse data based on section
                if current_section == "polygons":
                    try:
                        polygon_data = ast.literal_eval(line)
                        print(f"Polygon data: {polygon_data}")
                        if isinstance(polygon_data, tuple):
                            polygons.append(polygon_data)
                    except Exception as e:
                        print(f"Error parsing polygon: {e}")
                elif current_section == "units":
                    try:
                        unit_data = ast.literal_eval(line)
                        if isinstance(unit_data, tuple):
                            units.append(unit_data)
                    except Exception as e:
                        print(f"Error parsing unit: {e}")

    except Exception as e:
        print(f"Error loading map data: {e}")

    return polygons, units, node_spacing

map_path: str = r"map_files\map_test1.txt"

data = load_map_data(map_path)

for i in data[0]:
    print(i)