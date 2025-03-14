
import numpy as np 
import matplotlib.pyplot as plt 
from scipy.spatial import Delaunay 

# A 2D array of points
polygon = np.array([(650, 350), (1050, 400), (1000, 450)]) 

# Perform Delaunay triangulation
tri = Delaunay(polygon)

# Efficient way to output each sub-triangle as a tuple of the 3 coordinates
triangles = polygon[tri.simplices]
for triangle in triangles:
    print(tuple(map(tuple, triangle)))

# Visualize the triangulation 
plt.triplot(polygon[:,0], polygon[:,1], tri.simplices.copy()) 
plt.plot(polygon[:,0], polygon[:,1], 'o') 
plt.show() 