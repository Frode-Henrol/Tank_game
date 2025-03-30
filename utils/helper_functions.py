import numpy as np
import ast  
import itertools
from typing import Any


def coord_to_coordlist(coordinat_list: list) -> list:
    """Takes a list of coordinates (polygon) and makes tuples representing each line"""
    new_coordinat_list = []
    length = len(coordinat_list)

    # Connect polygon
    for i in range(length-1):
        new_coordinat_list.append((coordinat_list[i], coordinat_list[i+1]))
    
    # close the polygon
    new_coordinat_list.append((coordinat_list[-1], coordinat_list[0]))
    
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
                        polygon_points = ast.literal_eval(line)
                        if isinstance(polygon_points, list):
                            polygons.append(polygon_points)
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

def check_triangle(triangle: list[tuple], point: tuple) -> bool:
    """Checks if a point is inside a triangle

    Args:
        triangle (list[tuple])
        point (tuple)

    Returns:
        bool: true if inside false if outside
    """
    
    # Get all permutations of the triangle vertices
    permutations = itertools.permutations(triangle)
    detected = False
    # We need to look at potentiel all permutations of the triangle, since some choices of A B C corners can led to division by zero error
    # Even though its a perfect valid triangle:
    for perm in permutations:
        Ax, Ay = perm[0]
        Bx, By = perm[1]
        Cx, Cy = perm[2]
        Px, Py = point

        # Try using the formula to check if point is inside triangle. Source: https://www.youtube.com/watch?v=HYAgJN3x4GA&ab_channel=SebastianLague
        try:
            w1 = (Ax * (Cy - Ay) + (Py - Ay) * (Cx - Ax) - Px * (Cy - Ay)) / ((By - Ay) * (Cx - Ax) - (Bx - Ax) * (Cy - Ay))
            w2 = (Py - Ay - w1 * (By - Ay)) / (Cy - Ay)

            if w1 >= 0 and w2 >= 0 and (w1 + w2) <= 1:
                detected = True
                
        except ZeroDivisionError:
            print("Division with 0, trying next permutation...")
            continue  # Try the next permutation
        
    return detected

# UNUSED
def generate_polygon_coordinates(polygon: list[tuple[int,int]], spacing: int) -> list[tuple[int,int]]:
    """
    Generates evenly spaced coordinates along the edges of a polygon.
    
    Args:
        polygon (List[Tuple[int, int]]): A list of tuples representing the polygon's corner coordinates.
        spacing (int): The distance between consecutive points along the edges.
    
    Returns:
        List[Tuple[int, int]]: A list of coordinates along the polygon's edges, including its corners.
    """
    points = []
    num_vertices = len(polygon)
    
    for i in range(num_vertices):
        start = np.array(polygon[i])
        end = np.array(polygon[(i + 1) % num_vertices])  # Loop back to the first point
        
        # Compute the distance and direction
        edge_vector = end - start
        edge_length = np.linalg.norm(edge_vector)
        direction = edge_vector / edge_length  # Unit vector
        
        # Add points along the edge, starting from 'start'
        num_points = int(edge_length // spacing)  # Number of points to add
        for j in range(num_points + 1):  # Include the end point
            new_point = start + j * spacing * direction
            points.append(tuple(map(int, new_point)))  # Convert to integer tuple
    
    return sorted(set(points), key=lambda p: (p[0], p[1]))


def toggle_bool(obj: Any, attr_name: str) -> None: 
    """Toggles a boolean attribute given its name as a string."""
    if hasattr(obj, attr_name):  # Check if attribute exists
        current_value = getattr(obj, attr_name)  # Get the current value
        if isinstance(current_value, bool):  # Ensure it's a boolean
            setattr(obj, attr_name, not current_value)  # Toggle it
            print(f"Toggled {attr_name}")
        else:
            raise ValueError(f"Attribute '{attr_name}' is not a boolean.")
    else:
        raise AttributeError(f"'{obj.__class__.__name__}' has no attribute '{attr_name}'")
    

def distance(coord1: tuple, coord2: tuple) -> float:
    """Finds distance between 2 coordinates"""
    x1, y1 = coord1
    x2, y2 = coord2
    return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)