
import matplotlib.pyplot as plt
import numpy as np


# UNUSED - CONVERTED TO CYTHON!
def line_intersection(p1: tuple, p2: tuple, p3: tuple, p4: tuple) -> tuple | None:
    """Finds the intersection coord of two line segments if it exists. Returns the coord or none"""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    # Early bounding box rejection
    if (max(x1, x2) < min(x3, x4) or min(x1, x2) > max(x3, x4) or
        (max(y1, y2) < min(y3, y4) or min(y1, y2) > max(y3, y4))):
        return (-1.0, -1.0)
    
    # Calculate determinants
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        
    # If denominator is zero, the lines are parallel or coincident
    if denominator == 0:
        return (-1.0, -1.0)  # No intersection
    
    # Compute the intersection point using Cramer's Rule    
    px = ((x1*y2 - y1*x2) * (x3 - x4) - (x1 - x2) * (x3*y4 - y3*x4)) / denominator
    py = ((x1*y2 - y1*x2) * (y3 - y4) - (y1 - y2) * (x3*y4 - y3*x4)) / denominator

    epsilon = 1e-9
    if (min(x1, x2) - epsilon <= px <= max(x1, x2) + epsilon and 
        min(y1, y2) - epsilon <= py <= max(y1, y2) + epsilon and
        min(x3, x4) - epsilon <= px <= max(x3, x4) + epsilon and
        min(y3, y4) - epsilon <= py <= max(y3, y4) + epsilon):
        return (px, py)  # Intersection point
    
    return (-1.0, -1.0)  # The intersection is outside the segment

def find_normal_vectors(start_point: tuple, end_point: tuple) -> tuple:
    """Returns two possible unit normal vectors to the line segment."""
    x1, y1 = start_point
    x2, y2 = end_point
    
    # Compute direction vector
    dx = x2 - x1
    dy = y2 - y1
    
    # Normalize to unit length
    length = np.sqrt(dx**2 + dy**2)
    if length == 0:
        raise ValueError("Start and end points must be different")
    
    dx /= length
    dy /= length
    
    # Return two perpendicular unit normal vectors  
    return (-dy, dx), (dy, -dx)
    
def find_deflect_vector(normal_vector: tuple, vector_to_deflect: tuple) -> tuple:
    
    # Hvis 2 taller under kommer under/lig 1 så vil skudene stoppe ved vægge og give en fed effect (kunne bruges til noget visuelt) over 2 vil bounce give mere fart og mellem 2-1 vil skud blive langsomere
    return vector_to_deflect - 2 * (np.array(vector_to_deflect) @ np.array(normal_vector)) * np.array(normal_vector)
    

if __name__ == "__main__":
        # Example usage
    p1 = (-100, 0)
    p2 = (100, 0)
    p3 = (10, 2)
    p4 = (15, -2)

    # Find the 2 normal vectors
    nv_p1, nv_p2 = find_normal_vectors(p1, p2)

    print(f"{nv_p1},{nv_p2}")

    projectile_vector = (p4[0] - p3[0], p4[1] - p3[1])

    deflect_v = find_deflect_vector(nv_p1, projectile_vector)

    print(f"Deflect v: {deflect_v}")

    intersection = line_intersection(p1, p2, p3, p4)
    print("Intersection:", intersection)

    if intersection != None:
        # Move tangent vector to intersection:
        ix, iy = intersection

        # Unpack the 2 normal vector points
        nv1_x, nv1_y  = nv_p1
        nv2_x, nv2_y  = nv_p2

        # Add intersection amount to x and y
        nv_p1 = nv1_x + ix, nv1_y + iy
        nv_p2 = nv2_x + ix, nv2_y + iy

    print(f"{nv_p1},{nv_p2}")

    fig, ax = plt.subplots()
    ax.plot([p1[0],p2[0]],[p1[1],p2[1]], "red", label="Line 1")
    ax.plot([p3[0],p4[0]],[p3[1],p4[1]], "blue", label="Line 2")

    if intersection != None:
        # Normal vektor:
        ax.plot([nv_p1[0],nv_p2[0]],[nv_p1[1],nv_p2[1]], "green", label="Normal vektor")

        # Deflect vektor:
        # adds deflect vector to the intercept point. 
        ax.plot([ix, ix + deflect_v[0]],[iy, iy + deflect_v[1]], "purple", label="Deflect vektor")

        # Intersect point:
        ax.plot([intersection[0]],[intersection[1]],"o",label="Intersect")

    if intersection == None:
        print("No intersect")
        
    ax.legend()

    plt.show()
