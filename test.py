
import matplotlib.pyplot as plt
import numpy as np

def line_intersection(p1, p2, p3, p4):
    """Finds the intersection of two line segments if it exists."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    # Calculate determinants
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    
    # If denominator is zero, the lines are parallel or coincident
    if denominator == 0:
        return None  # No intersection

    # Compute the intersection point using Cramer's Rule    
    px = ((x1*y2 - y1*x2) * (x3 - x4) - (x1 - x2) * (x3*y4 - y3*x4)) / denominator
    py = ((x1*y2 - y1*x2) * (y3 - y4) - (y1 - y2) * (x3*y4 - y3*x4)) / denominator

    # Check if the intersection point is within both line segments
    if (min(x1, x2) <= px <= max(x1, x2) and 
        min(y1, y2) <= py <= max(y1, y2) and
        min(x3, x4) <= px <= max(x3, x4) and
        min(y3, y4) <= py <= max(y3, y4)):
        return (px, py)  # Intersection point

    return None  # The intersection is outside the segment

def find_normal_vector(start_point, end_point):
    """Normilized vector"""
    x1, y1 = start_point
    x2, y2 = end_point
    
    dx = x2 - x1
    dy = y2 - y1
    
    # Normilize len
    v_len = np.sqrt(dx**2 + dy**2)
    dx /= v_len
    dy /= v_len
    
    return (-dy,dx),(dy,-dx)
    
    
def find_deflect_vector(normal_vector, vector_to_deflect):
    """???"""
    r = vector_to_deflect - 2 * (vector_to_deflect * normal_vector) * normal_vector
    return r
    
# Example usage
p1 = (0, 0)
p2 = (10, 0)
p3 = (3, -1)
p4 = (20, 20)

# Find 2 point of the normal vector
nv_p1, nv_p2 = find_normal_vector(p1, p2)

print(f"{nv_p1},{nv_p2}")

intersection = line_intersection(p1, p2, p3, p4)
print("Intersection:", intersection)

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

# Normal vektor:
ax.plot([nv_p1[0],nv_p2[0]],[nv_p1[1],nv_p2[1]], "green", label="Normal vektor")
#ax.plot([intersection[0],nv_p1[0]],[intersection[1],nv_p1[1]], "green", label="Normal vektor")

if intersection != None:
    ax.plot([intersection[0]],[intersection[1]],"o",label="Intersect")

ax.legend()

plt.show()
