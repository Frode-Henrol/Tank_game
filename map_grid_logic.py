import pygame as pg
import utils.helper_functions as hf
import numpy as np
import triangle as tr

    
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
        
def find_valid_nodes(corners: list[tuple], node_spacing: int, polygons: list[list[tuple]]) -> list[tuple]:
    """ Find all nodes in a grid that is not inside of a polygon

    Args:
        corners (list[tuple]): list of corners coordinates
        node_spacing (int): how far between each node
        polygons list[list[tuple]]: list of polygons. A polygon is a list of points (tuples)

    Returns:
        list[tuple]: the valid node list - nodes that are not inside a polygon
    """

    bot_left, bot_right, top_right, top_left = corners[0], corners[1], corners[2], corners[3]

    grid_size_x = top_right[0] - top_left[0]
    grid_size_y = bot_right[1] - top_right[1]

    start_offset = node_spacing // 2

    valid_nodes = []  # List to store nodes outside any polygon

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
                
    return valid_nodes



if __name__ == "__main__":
    # Showcase:
    
    # Load the map data
    polygons, units = hf.load_map_data(r"map_files\map_test1.txt")

    # Remove border polygon:
    corners = polygons.pop(0)
    
    
    valid_nodes = find_valid_nodes(corners, 50, polygons)
    
    print(f"Valid nodes: {len(valid_nodes)}")
        