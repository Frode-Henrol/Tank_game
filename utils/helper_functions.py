import numpy as np
import ast  # For safely evaluating the string representation of the data
import math

def coord_to_coordlist(coordinat_list: list) -> list:
    """Takes a list of coordinates (polygon) and makes tuples representing each line"""
    new_coordinat_list = []
    length = len(coordinat_list)

    # Connect polygon
    for i in range(length-1):
        new_coordinat_list.append((coordinat_list[i], coordinat_list[i+1]))
    
    # close the polygon
    new_coordinat_list.append((coordinat_list[-1], coordinat_list[0]))
    
    #return [((420, 420), (480, 420)),((400,100),(600,100))] #------------------------------------------------------------!
    return new_coordinat_list

def get_vector_magnitude(vector: list) -> float:
    return np.sqrt(vector[0] ** 2 + vector[1] ** 2)

def unit_vector(from_point: tuple, to_point: tuple) -> tuple:
    """Returns the unit vector pointing from from_point to to_point."""
    dx, dy = to_point[0] - from_point[0], to_point[1] - from_point[1]
    length = get_vector_magnitude([dx, dy])
    
    if length == 0:
        return (0, 0)  # Avoid division by zero
    
    return (dx / length, dy / length)


def load_map_data(map_name):
    """Load the map and polygons/units from the text file."""
    polygons = []
    units = []

    try:
        with open(map_name, "r") as f:
            lines = f.readlines()

            # Parse the lines to find the relevant sections
            current_section = None
            for line in lines:
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue
                
                # Identify the section headers
                if line == "Polygons:":
                    current_section = "polygons"
                    continue
                elif line == "Units:":
                    current_section = "units"
                    continue
                
                # Depending on the current section, parse the appropriate data
                if current_section == "polygons" and line.startswith('['):
                    polygon_points = ast.literal_eval(line)
                    polygons.append(polygon_points)
                elif current_section == "units" and line.startswith('('):
                    unit_data = ast.literal_eval(line)
                    units.append(unit_data)

    except Exception as e:
        print(f"Error loading map data: {e}")

    return polygons, units
