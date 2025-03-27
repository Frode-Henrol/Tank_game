import pygame as pg
import utils.helper_functions as hf
import numpy as np
import triangle as tr
import heapq
from collections import defaultdict
import time 
import math


# Collection of function used for path finding

# --- helpers ---
def split_polygon_into_triangles(polygon: list[tuple]) -> list[tuple]:
    """ Splits polygon into triangles

    Args:
        polygon (list[tuple]): list of coords defining the coords

    Returns:
        list[tuple]: list of triangles
    """
    
    segments = {
        "vertices": polygon,
        "segments": [[i, i+1] for i in range(len(polygon)-1)] + [[len(polygon)-1, 0]]  # Close the loop 
    }
    
    # Perform constrained triangulation
    triangulation = tr.triangulate(segments, "p")
    
    # Extract vertices and triangles
    vertices = triangulation["vertices"]  # All unique vertices
    triangles = triangulation["triangles"]  # Indices of triangles

    # Convert to list of lists of tuples (each triangle as 3 coordinate points)
    triangle_list = [[tuple(vertices[i]) for i in triangle] for triangle in triangles]
    
    return triangle_list
        
def find_valid_nodes(corners: list[tuple], node_spacing: int, polygons: list[list[tuple]]) -> np.ndarray:
    """ Find all nodes in a grid that is not inside of a polygon

    Args:
        corners (list[tuple]): list of corners coordinates
        node_spacing (int): how far between each node
        polygons list[list[tuple]]: list of polygons. A polygon is a list of points (tuples) (EXCLUDING THE CORNER POLYGON!)

    Returns:
        list[tuple]: the valid node list - nodes that are not inside a polygon
        ndarray: a grid with invalid nodes marked as 1 and valid as 0
    """

    bot_left, bot_right, top_right, top_left = corners[0], corners[1], corners[2], corners[3]

    grid_size_x = top_right[0] - top_left[0]
    grid_size_y = bot_right[1] - top_right[1]

    start_offset = node_spacing // 2
    grid_nodes_x = grid_size_x // node_spacing
    grid_nodes_y = grid_size_y // node_spacing

    valid_nodes = []  # List to store nodes outside any polygon
    map_grid = np.zeros([grid_nodes_y,grid_nodes_x])
    print(grid_nodes_y,grid_nodes_x)
    print(f"{map_grid=}")
    
    
    # Loop through the grid and collect valid nodes
    for x in range(start_offset, grid_size_x, node_spacing):
        for y in range(start_offset, grid_size_y, node_spacing):
            
            # Find offset to map top left corner
            offset_x, offset_y = top_left
            node = (x + offset_x, y + offset_y)
            
            # Check if this node is inside any of the polygons sub triangles
            is_inside = False
            for polygon in polygons:
                triangles = split_polygon_into_triangles(np.array(polygon))
                for triangle in triangles:
                    if hf.check_triangle(triangle, node):
                        is_inside = True
                        
            # If the node (point) is not inside then we add it to valid nodes
            if not is_inside:
                valid_nodes.append(node)
            else:
                map_grid[y//node_spacing,x//node_spacing] = 1
                
    return map_grid, valid_nodes

def grid_to_dict(grid: np.ndarray) -> dict:
        
    y_size, x_size = grid.shape

    coord_list = []

    # Define relative neighbor positions
    k = 1   # Hardcoded at 1
    neighbors = [(-k,-k), (0,-k), (k,-k), (-k,0), (k,0), (-k,k), (0,k), (k,k)]

    coord_dict = defaultdict(list)

    for y in range(y_size):
        for x in range(x_size):
            coord_list.append((x, y))  # Store the coordinate
            
            temp_coord = []
            
            for dx, dy in neighbors:
                nx, ny = x + dx, y + dy  # Compute neighbor coordinates
                
                # Ensure the neighbor is within bounds
                if 0 <= nx < x_size and 0 <= ny < y_size and grid[ny, nx] == 0:
                    
                    # Check for diagonal neighbors' validity
                    if dx == -1 and dy == -1:  # Top-left
                        coord =((nx,ny), 1.4)
                        if grid[y, x-1] == 1 or grid[y-1, x] == 1:
                            continue  
                    elif dx == 1 and dy == -1:  # Top-right
                        coord =((nx,ny), 1.4)
                        if grid[y, x+1] == 1 or grid[y-1, x] == 1:
                            continue
                    elif dx == -1 and dy == 1:  # Bottom-left
                        coord =((nx,ny), 1.4)
                        if grid[y, x-1] == 1 or grid[y+1, x] == 1:
                            continue
                    elif dx == 1 and dy == 1:  # Bottom-right
                        coord =((nx,ny), 1.4)
                        if grid[y, x+1] == 1 or grid[y+1, x] == 1:
                            continue
                    else:
                        coord =((nx,ny), 1)
                        
                    temp_coord.append(coord)  # Append valid neighbor
            
            coord_dict[(x,y)] = (temp_coord)
            
            #print(f"({x}, {y}) -> Neighbors: {temp_coord}")

    return coord_dict
# --- helpers ---

# --- func to use ---
def get_mapgrid_dict(polygons: list[list[tuple]], node_spacing: int) -> dict:
    
    all_triangles = []
    for polygon in polygons:
        triangles = split_polygon_into_triangles(np.array(polygon))
        all_triangles += triangles
        
    if len(all_triangles) > 2:
        print("get_mapgrad_dict: all_triagnles is empty")
        # Remove map triangles (two)
        all_triangles.pop(0)
        all_triangles.pop(0)


    corners = polygons.pop(0)
    
    # Node spacing is the quality of the pathfinding grid
    map_grid, valid_nodes = find_valid_nodes(corners, node_spacing, polygons)    

    # Convert grid to a dictionary that stores each coords(nodes) neighbors and costs (only ran once per map)
    return grid_to_dict(map_grid)

# This is used by a unit each time it need to find a path
def find_path(grid_dict: dict[tuple, list], start_coord: tuple[int, int], end_coord: tuple[int, int]):
    """Optimized A* pathfinding"""
    
    open_list = [(0, start_coord)]  # Priority queue (min heap)
    heapq.heapify(open_list)  # Ensures it's a valid heap

    g_cost = {start_coord: 0}  # Cost from start
    came_from = {}  # To reconstruct path
    closed_list = set()  # Explored nodes

    while open_list:
        _, current = heapq.heappop(open_list)  # Pop lowest cost node

        if current == end_coord:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start_coord)
            return path[::-1]

        closed_list.add(current)

        # Explore neighbors
        current_g = g_cost[current]
        for neighbor, cost in grid_dict.get(current, []):
            if neighbor in closed_list:
                continue

            new_g = current_g + cost
            if neighbor not in g_cost or new_g < g_cost[neighbor]:
                g_cost[neighbor] = new_g
                f_cost = new_g + math.hypot(neighbor[0] - end_coord[0], neighbor[1] - end_coord[1])
                heapq.heappush(open_list, (f_cost, neighbor))
                came_from[neighbor] = current

    return None  # No path found

# These 2 functions convert from grid coords to pygame coords
def pygame_to_grid(pygame_coord: tuple, top_left: tuple, node_spacing: int):
    """Convert Pygame (pixel) coordinates to grid (row, col)"""
    x, y = pygame_coord
    grid_x = (x - top_left[0]) // node_spacing
    grid_y = (y - top_left[1]) // node_spacing
    return int(grid_x), int(grid_y)  # Ensure integer output

def grid_to_pygame(grid_coord: tuple, top_left: tuple, node_spacing: int):
    """Convert grid (row, col) coordinates to Pygame (pixel)"""
    grid_x, grid_y = grid_coord
    x = grid_x * node_spacing + top_left[0] + node_spacing // 2
    y = grid_y * node_spacing + top_left[1] + node_spacing // 2
    return x, y