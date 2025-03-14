import pygame as pg
import utils.helper_functions as hf
import numpy as np
import triangle as tr

# Need to be in the tank folder to work

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
        
# Initialize Pygame
pg.init()

# Set the screen dimensions (larger than the grid)
screen_width = 1600
screen_height = 800
screen = pg.display.set_mode((screen_width, screen_height))
pg.display.set_caption("Polygon Drawer")

# Load the map data
polygons, units = hf.load_map_data(r"map_files\map_test1.txt")

# Remove border polygon:
polygons.pop(0)

# Define the corners for the grid and setup
corners = [(500, 750), (1400, 750), (1400, 300), (500, 300)]

bot_left, bot_right, top_right, top_left = corners[0], corners[1], corners[2], corners[3]

node_spacing = 50

grid_size_x = top_right[0] - top_left[0]
grid_size_y = bot_right[1] - top_right[1]

grid_nodes_x = grid_size_x // 50
grid_nodes_y = grid_size_y // 50

start_offset = node_spacing // 2

valid_nodes = []  # List to store nodes outside any polygon
all_triangles = []

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
            valid_nodes.append(node)  # Add to valid_nodes if not inside any polygon

for polygon in polygons:
    triangles = split_polygon_into_triangles(np.array(polygon))
    all_triangles += triangles
    
print(all_triangles)


# Colors for drawing polygons and nodes
POLYGON_COLOR = (0, 255, 0)  # Green for polygons
NODE_COLOR = (0, 0, 255)  # Blue for nodes

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
    
    # Handle events (e.g., quit the game)
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
            

    # Update the screen
    pg.display.flip()

# Quit Pygame
pg.quit()
