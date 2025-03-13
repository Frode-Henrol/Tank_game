import pygame as pg
from utils.helper_functions import load_map_data


# Initialize Pygame
pg.init()

# Set the screen dimensions (larger than the grid)
screen_width = 1600
screen_height = 800
screen = pg.display.set_mode((screen_width, screen_height))
pg.display.set_caption("Polygon Drawer")

# Load the map data
polygons, units = load_map_data(r"map_files\map_test1.txt")

# Remove border polygon:
polygons.pop(0)

# Define the corners for the grid and setup
corners = [(500, 750), (1400, 750), (1400, 300), (500, 300)]

bot_left, bot_right, top_right, top_left = corners[0], corners[1], corners[2], corners[3]

node_spacing = 50

grid_size_x = top_right[0] - top_left[0]
grid_size_y = bot_right[1] - top_right[1]

print(f"{grid_size_x} {grid_size_y}")

grid_nodes_x = grid_size_x // 50
grid_nodes_y = grid_size_y // 50

start_offset = node_spacing // 2
print(f"{start_offset=} {grid_nodes_x=} {node_spacing=}")

valid_nodes = []  # List to store nodes outside any polygon

# Loop through the grid and collect valid nodes
for x in range(start_offset, grid_size_x, node_spacing):
    for y in range(start_offset, grid_size_y, node_spacing):
        
        # Find offset to map top left corner
        offset_x, offset_y = top_left
        node = (x + offset_x, y + offset_y)
        
        # Check if this node is inside any of the polygons
        is_inside = False
        for poly in polygons:
            if pg.draw.polygon(screen, (0, 255, 0), poly).collidepoint(node):
                is_inside = True
                break  # Break if the node is inside any polygon
        
        if not is_inside:
            valid_nodes.append(node)  # Add to valid_nodes if not inside any polygon



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

    # Handle events (e.g., quit the game)
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
            
        if event.type == pg.MOUSEBUTTONUP:
            pos = pg.mouse.get_pos()
            for poly in polygons:
                if pg.draw.polygon(screen, (0, 255, 0), poly).collidepoint(pos):
                    print("Mouse inside polygon")
            

    # Update the screen
    pg.display.flip()

# Quit Pygame
pg.quit()
