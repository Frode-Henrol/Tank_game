import pygame as pg
import utils.helper_functions as hf
import numpy as np
import triangle as tr
import heapq
from collections import defaultdict
    
    
def split_polygon(polygon: list[tuple]) -> list[list[tuple]]:
    """ Split polygon into triangles

    Args:
        polygon (list[tuple]): A polygon is a list of points (tuples)

    Returns:
        list[list[tuple]]: list of triangles. A triangle is a list of points (tuples)
    """
    # Define input for triangle
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
        polygons list[list[tuple]]: list of polygons. A polygon is a list of points (tuples)

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
    
    # TODO Make so functions reutrns a grid?
    
    # Loop through the grid and collect valid nodes
    for x in range(start_offset, grid_size_x, node_spacing):
        for y in range(start_offset, grid_size_y, node_spacing):
            
            # Find offset to map top left corner
            offset_x, offset_y = top_left
            node = (x + offset_x, y + offset_y)
            
            # Check if this node is inside any of the polygons sub triangles
            is_inside = False
            for polygon in polygons:
                triangles = split_polygon(np.array(polygon))
                for triangle in triangles:
                    if hf.check_triangle(triangle, node):
                        is_inside = True
                        
            # If the node (point) is not inside then we add it to valid nodes
            if not is_inside:
                valid_nodes.append(node)
            else:
                map_grid[y//node_spacing,x//node_spacing] = 1
                
    return map_grid, valid_nodes


# ==========

def distance(current_coord: tuple[int, int], goal_coord: tuple[int, int]) -> float:
    x1, y1 = current_coord
    x2, y2 = goal_coord
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def find_path(grid_dict: dict[tuple, list], start_coord: tuple[int, int], end_coord: tuple[int, int]):
    g_cost = {start_coord: 0}  # Actual cost from start
    came_from = {}  # To reconstruct path
    open_list = []
    heapq.heappush(open_list, (0, start_coord))  # (f, coord)
    closed_list = set()  # Fully explored nodes

    while open_list:
        _, pre_coord = heapq.heappop(open_list)  # Get node with lowest f

        if pre_coord == end_coord:  # If goal is reached, reconstruct path
            print(f"Found end")
            path = []
            while pre_coord in came_from:
                path.append(pre_coord)
                pre_coord = came_from[pre_coord]
            path.append(start_coord)
            return path[::-1]  # Return reversed path

        closed_list.add(pre_coord)

        # Explore neighbors        
        for suc_coord, suc_cost in grid_dict[pre_coord]:
            if suc_coord in closed_list:
                continue  # Skip already processed nodes

            new_g = g_cost[pre_coord] + suc_cost  # Compute new cost
            new_f = new_g + distance(suc_coord, end_coord)

            # Only update if it's a better path
            if suc_coord not in g_cost or new_g < g_cost[suc_coord]:
                g_cost[suc_coord] = new_g
                came_from[suc_coord] = pre_coord
                #print(f"Pushing {suc_coord} Cost: {new_f}")
                heapq.heappush(open_list, (new_f, suc_coord))

    return None  # No path found
      
def grid_to_dict(grid: np.ndarray, node_spacing: int) -> dict:
        
    y_size, x_size = grid.shape

    coord_list = []

    # Define relative neighbor positions
    k = node_spacing
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
        
def grid_to_dict_GPT(grid: np.ndarray) -> dict:
    y_size, x_size = grid.shape
    coord_dict = defaultdict(list)

    # Define relative neighbor positions
    neighbors = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

    for y in range(y_size):
        for x in range(x_size):
            temp_coord = []
            
            for dx, dy in neighbors:
                nx, ny = x + dx, y + dy  # Compute neighbor coordinates

                # Ensure the neighbor is within bounds
                if 0 <= nx < x_size and 0 <= ny < y_size and grid[ny, nx] == 0:
                    
                    # Check for diagonal neighbors' validity
                    if (dx, dy) in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                        # Check for blocked diagonals
                        if grid[y, x-1] == 1 or grid[y-1, x] == 1 if dy == -1 else grid[y+1, x] == 1 or grid[y, x+1] == 1:
                            continue  # Skip invalid diagonal moves
                        temp_coord.append(((nx, ny), 1.4))
                    else:
                        temp_coord.append(((nx, ny), 1))  # Add regular move (horizontal/vertical)

            coord_dict[(x, y)] = temp_coord

    return coord_dict


# ==========

def split_polygon_into_triangles(polygon: list[tuple]) -> list[tuple]:
    # Define input for triangle
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


def pygame_to_grid(pygame_coord, top_left, node_spacing):
    """Convert Pygame (pixel) coordinates to grid (row, col)"""
    x, y = pygame_coord
    grid_x = (x - top_left[0]) // node_spacing
    grid_y = (y - top_left[1]) // node_spacing
    return int(grid_x), int(grid_y)  # Ensure integer output

def grid_to_pygame(grid_coord, top_left, node_spacing):
    """Convert grid (row, col) coordinates to Pygame (pixel)"""
    grid_x, grid_y = grid_coord
    x = grid_x * node_spacing + top_left[0] + node_spacing // 2
    y = grid_y * node_spacing + top_left[1] + node_spacing // 2
    return x, y



if __name__ == "__main__":
    # Load the map data
    polygons, units = hf.load_map_data(r"map_files\map_test1.txt")

    all_triangles = []
    for polygon in polygons:
        triangles = split_polygon_into_triangles(np.array(polygon))
        all_triangles += triangles

    # Remove map triangles (two)
    all_triangles.pop(0)
    all_triangles.pop(0)

    # Remove border polygon:
    corners = polygons.pop(0)
    
    # Node spacing is the quality of the pathfinding grid
    node_spacing = 50
    map_grid, valid_nodes = find_valid_nodes(corners, node_spacing, polygons)    
    print(f"Valid nodes: {valid_nodes}")
        
    # Initialize Pygame
    pg.init()

    # Set the screen dimensions (larger than the grid)
    screen_width = 1600
    screen_height = 800
    screen = pg.display.set_mode((screen_width, screen_height))
    pg.display.set_caption("Polygon Drawer")
        
    # Colors for drawing polygons and nodes
    POLYGON_COLOR = (0, 255, 0)  # Green for polygons
    NODE_COLOR = (0, 0, 255)  # Blue for nodes

    # Path to plot on pygame map (start empty):
    lines = []
    start, end = (0,0), (0,0)
    start_coord, end_coord = (0,0), (0,0)

    # Convert grid to a dictionary that stores each coords(nodes) neighbors and costs (only ran once per map)
    grid_dict = grid_to_dict(map_grid, 1)

    # Main game loop
    running = True
    while running:
        screen.fill((255, 255, 255))  # Fill screen with white
        
        
        # Get mouse position
        pos = pg.mouse.get_pos()

        # Loop through the polygons and draw them
        for poly in polygons:
            pg.draw.polygon(screen, POLYGON_COLOR, poly)

        # Draw valid nodes (those not inside any polygon)
        for node in valid_nodes:
            pg.draw.circle(screen, NODE_COLOR, node, 5)  # Draw nodes as circles

        # Drawtriangles:
        for triangle in all_triangles:
            pg.draw.polygon(screen, (0,100,0), triangle, 3)
            
        # Draw path
        for c1, c2 in lines:
            pg.draw.line(screen, "purple", c1, c2, 5)  # Already converted to Pygame
            
            
        # Draw start and end
        pg.draw.circle(screen, "green", start, 5)
        pg.draw.circle(screen, "red", end, 5)

        # Handle events (e.g., quit the game)
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_s:
                    mouse_pos = pg.mouse.get_pos()
                    start = mouse_pos
                    start_coord = pygame_to_grid(mouse_pos, corners[3], node_spacing)
                    print(f"Start (grid): {start}")
                    
                    
                if event.key == pg.K_e:
                    mouse_pos = pg.mouse.get_pos()
                    end = mouse_pos
                    end_coord = pygame_to_grid(mouse_pos, corners[3], node_spacing)
                    print(f"End (grid): {end}")

                    # Find path in grid coordinates
                    path = find_path(grid_dict, start_coord, end_coord)

                    # Convert path from grid coordinates to Pygame coordinates for drawing
                    if path != None:
                        lines = [(grid_to_pygame(path[i], corners[3], node_spacing), 
                                grid_to_pygame(path[i + 1], corners[3], node_spacing)) 
                                for i in range(len(path) - 1)]
                    
                    print(f"{lines=}")

                    

        # Update the screen
        pg.display.flip()

    # Quit Pygame
    pg.quit()


        