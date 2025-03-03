import sys
import pygame as pg
import numpy as np
import os
import csv


data_points_path = os.path.join(os.getcwd(),"Polygon_3D_model_test","data_points.txt")
data_connections_path = os.path.join(os.getcwd(),"Polygon_3D_model_test","data_connections.txt")

# Ctrl F for "SKAL RETTES" og se kommentarer

class Engine:
    def __init__(self):
        pg.init()
        self.clock = pg.time.Clock()
        self.fps = 60
        self.WINDOW_DIM = (800, 800)
        self.SCALE = 30
        self.screen = pg.display.set_mode(self.WINDOW_DIM)
        
        self.camera_coord = np.array([0.0,0,1])
        self.camera_direction = np.array([float(0),float(0),float(0)])
        self.camera_up_vector = np.array([float(0),float(0),float(1)])
        self.camera_yaw_angle = 0
        self.camera_pitch_angle = 0
        self.camera_angle_amount = 1
        
        self.world_up_vector = np.array([float(0),float(1),float(0)])
        
        # ===================== Everthing is in "units" ========================
        # Frustum Boundaries 
        self.left = -10
        self.right = 10
        self.top = 10
        self.bottom = -10
        
        # Closest and furthest distance to render
        self.near = 1
        self.far = 100
        
        # The transformed 3D points on 2D plane
        self.plane_coords = None
        
        self.setup() 

    def setup(self):
        """Load assets and initialize properties."""
        self.data_points = self.load_assets(data_points_path, dtype="float")
        self.data_connections = self.load_assets(data_connections_path, dtype="int")
        self.data_connections_matrix = self.get_connection_matrix(self.data_connections)
        self.homogen_coords = self.get_homogen_coords(self.data_points) # Unsused at the moment

    def get_connection_matrix(self, data):
    
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
        
    def get_homogen_coords(self, data):
        
        homogen_zero_matrix = np.zeros((len(data[0]) + 1,len(data))) # Create zero matrix and set last row to pure 1's
        homogen_zero_matrix[-1][:] = 1
        # Add the data to the matrix
        for i in range(len(data)):
            homogen_zero_matrix[:3,i] = data[i]
        
        print(f"{homogen_zero_matrix}")
        return homogen_zero_matrix
        
    def load_assets(self, filename: str, dtype: str):
        
        if dtype not in ["int","float"]:
            raise ValueError("Input type must be either 'int' or 'float'")
        
        with open(filename, "r", encoding="utf-8") as file:
            
            reader = csv.reader(file)
            
            if dtype == "float":
                data = [list(map(float, row)) for row in reader]
            if dtype == "int":
                data = [list(map(int, row)) for row in reader]
            
        print(f"{data=}")
        return data
        
    def rotate_model(self):
        pass
    
    def pan_model(self):
        pass
    
    def zoom_model(self):
        pass
        
    def move_to_coord(self):
        pass
    
    def init_game_objects(self):
        
        self.polygon = np.array([[0,5,-5],[5,-5,-5]])
    
    # Camera transformations ---------------------------------    
    # SKAL RETTES: Der er byttet rundt på pitch og yaw funktionaliteten........
    def yaw_cam(self, dir):
        if dir not in ["left","right"]:
            raise ValueError("Must be 'right' or 'left' for 'dir'.")
        
        if dir == "left":
            self.camera_yaw_angle += self.camera_angle_amount
        elif dir == "right":
            self.camera_yaw_angle -= self.camera_angle_amount
    
    def pitch_cam(self, dir):
        if dir not in ["up","down"]:
            raise ValueError("Must be 'up' or 'down' for 'dir'.")
        
        if dir == "up":
            self.camera_pitch_angle += self.camera_angle_amount
            if self.camera_pitch_angle > 90:
                print("Max pitch reached")
                self.camera_pitch_angle = 90
                return
            
        elif dir == "down":
            self.camera_pitch_angle -= self.camera_angle_amount
            if self.camera_pitch_angle < -90:
                print("Min pitch reached")
                self.camera_pitch_angle = -90
                return

    def update_cam(self):
        
        pitch_rad = np.radians(self.camera_pitch_angle)
        yaw_rad = np.radians(self.camera_yaw_angle)
        
        x = np.cos(pitch_rad)*np.sin(yaw_rad)
        y = np.sin(pitch_rad)
        z = np.cos(pitch_rad) * np.cos(yaw_rad)
        
        self.camera_direction[:] = x,y,z
        
        
        view_matrix = self.view_matrix(self.camera_coord, self.camera_direction)
        ort_proj_matrix = self.orthogonal_projection()
        
        
        # Transform into viewspace
        viewspace_coords = view_matrix @ self.homogen_coords
        
        # Map onto 2D plane
        plane_coords = ort_proj_matrix @ viewspace_coords
        
        
        self.plane_coords = plane_coords
        
        #print(plane_coords)
        #print(self.camera_direction)
        #print(self.camera_direction, self.camera_yaw_angle, self.camera_pitch_angle)

        
    def view_matrix(self, camera_position, camera_direction):
        # 1. Compute the target point the camera is looking at (camera_position + camera_direction)
        target = camera_position + camera_direction
        
        # 2. Compute forward vector (negative for OpenGL)
        forward = np.array(target - camera_position)
        
        # Ensure the forward vector is not a zero vector
        norm = np.linalg.norm(forward)
        if norm == 0:
            print("Warning: camera position and target are the same!")
            forward = np.array([0, 0, -1])  # Default forward vector, or handle as needed
        else:
            forward = forward / norm

        # 3. Compute right vector
        right = np.cross(self.world_up_vector, forward)
        right = right / np.linalg.norm(right) if np.linalg.norm(right) != 0 else np.array([1, 0, 0])  # Ensure non-zero right vector

        # 4. Compute up vector
        up = np.cross(forward, right)
        up = up / np.linalg.norm(up) if np.linalg.norm(up) != 0 else np.array([0, 1, 0])  # Ensure non-zero up vector

        # 5. Construct View Matrix
        view_matrix = np.array([
            [right[0], up[0], forward[0], -np.dot(right, camera_position)],
            [right[1], up[1], forward[1], -np.dot(up, camera_position)],
            [right[2], up[2], forward[2], -np.dot(forward, camera_position)],
            [0, 0, 0, 1]
        ])

        return view_matrix


    def orthogonal_projection(self):
        # Access the instance variables using self
        left = self.left
        right = self.right
        bottom = self.bottom
        top = self.top
        near = self.near
        far = self.far
        
        # Construct the orthogonal projection matrix
        projection_matrix = np.array([
            [2 / (right - left), 0, 0, -(right + left) / (right - left)],
            [0, 2 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
            [0, 0, -2 / (far - near), -(far + near) / (far - near)],
            [0, 0, 0, 1]
        ])
        
        return projection_matrix


    def handle_events(self):
        """Handle player inputs and game events."""
        keys = pg.key.get_pressed()
        if keys[pg.K_q]:
            pg.quit()
            sys.exit()
            
        if keys[pg.K_i]:
            # up
            self.pitch_cam(dir="up")
        if keys[pg.K_k]:
            # down
            self.pitch_cam(dir="down")
        if keys[pg.K_j]:
            # left
            self.yaw_cam(dir="left")
        if keys[pg.K_l]:
            # right
            self.yaw_cam(dir="right")

        
        for e in pg.event.get():
            match e.type:
                case pg.QUIT:
                    pg.quit()
                    sys.exit()
                    

    def draw(self):
        """Render all objects on the screen."""
        self.screen.fill("white")

        # Update camera and perform 3D to 2D projection
        self.update_cam()
        
        print(f"====== Updated coords ======")
        # Plane coords is scaled to fit the pygame window
        plane_coords_scaled = []
        if self.plane_coords is not None:
            # Draw the projected points
            print(f"{self.plane_coords}")
            for point in range(self.plane_coords.shape[1]):
                coord = self.plane_coords[:3, point]
                print(coord)
                
                # SKAL RETTES: lige nu er der bare gange med 10 fordi det passer OK med at se model
                # Dette skal ikke være hardcoded!
                # Use x, y directly (assuming it's 3D projection without homogeneous coordinates)
                x = coord[0]*10  # Use x-coordinate
                y = coord[1]*10  # Use y-coordinate
                
                # Adjust the coordinates to fit the screen
                # Here, scale by self.SCALE and offset by self.WINDOW_DIM[0]//2 and self.WINDOW_DIM[1]//2
                screen_x = int(self.WINDOW_DIM[0] // 2 + x * self.SCALE)
                screen_y = int(self.WINDOW_DIM[1] // 2 - y * self.SCALE)
                
                print(screen_x,screen_y)
                
                plane_coords_scaled.append((screen_x,screen_y))
                
                # Draw the point as a red circle
                pg.draw.circle(self.screen, "red", (screen_x, screen_y), 5)
                
        line_elements = self.get_line_elements(plane_coords_scaled, self.data_connections)
        
        for line in line_elements:
            pg.draw.line(self.screen, "red", line[0], line[1], 3)
                    

        pg.display.update()
        self.clock.tick(self.fps)

    def get_line_elements(self, plane_coords, data_connections):
        """Takes a list of the transformed plane coords (points) and data_connections (connection data for each point)
            and find each line element and save in list"""
        line_elements = set()
        
        # Loop over each point
        for i in range(len(plane_coords)):
            # Loop over each connection to the point:
            for connection in data_connections[i]:
                # Add all the line elements
                line_elements.add((plane_coords[i], plane_coords[connection-1]))

        return line_elements


    def run(self):
        """Main game loop."""
        while True:
            self.handle_events()
            self.draw()

   
if __name__ == "__main__":
    game = Engine()
    game.run()