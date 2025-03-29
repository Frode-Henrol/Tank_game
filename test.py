import numpy as np

def generate_polygon_coordinates(polygon, spacing):
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

# Example usage:
polygon = [(550, 750), (1350, 750), (1350, 300), (550, 300)]
spacing = 100
coordinates = generate_polygon_coordinates(polygon, spacing)
print(coordinates)
