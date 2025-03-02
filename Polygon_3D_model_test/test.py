
import csv
import numpy as np
import os

data_points_path = os.path.join(os.getcwd(),"Polygon_3D_model_test","data_connections.txt")

def load_assets(filename: str, type: str):
    """Load and scale game assets (e.g., images)."""
    with open(data_points_path, "r", encoding="utf-8") as file:
        
        reader = csv.reader(file)
        if type == "float":
            print("float")
            data = [list(map(float, row)) for row in reader]
        if type == "int":
            print("int")
            data = [list(map(int, row)) for row in reader]
        
    return data


data = load_assets(data_points_path, type="int")

#print(data)

def get_connection_matrix(data):
    
    data_len = len(data)
    zero_matrix = np.zeros((data_len, data_len))
    
    # Loop over each point i
    for i in range(data_len):
        
        # Get connections for specific point
        connections_point = data[i]
        
        # Go over each connection the point connects to
        for connection in connections_point:
            
            # Insert 1 where a connection between 2 points are
            zero_matrix[i][connection-1] = 1
    
    return zero_matrix


def get_homogen_coords(data):
    homogen_zero_matrix = np.zeros((len(data[0]) + 1,len(data))) # Create zero matrix and set last row to pure 1's
    homogen_zero_matrix[-1][:] = 1

    # Add the data to the matrix
    for i in range(len(data)):
        homogen_zero_matrix[:3,i] = data[i]

    return homogen_zero_matrix
        
    



print(data)


    
    
    
    
