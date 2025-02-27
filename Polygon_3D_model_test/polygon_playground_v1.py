import sys
import pygame as pg
import numpy as np
import os
import csv

data_points_path = os.path.join(os.getcwd(),"Polygon_3D_model_test","data_points.txt")
data_connections_path = os.path.join(os.getcwd(),"Polygon_3D_model_test","data_connections.txt")

class Engine:
    def __init__(self):
        pg.init()
        self.clock = pg.time.Clock()
        self.fps = 60
        self.WINDOW_DIM = (800, 800)
        self.SCALE = 30
        self.screen = pg.display.set_mode(self.WINDOW_DIM)
        self.camera_coord = np.array([0.0,0])
        
        self.camera_direction = np.array([float(0),float(0),float(0)])
        self.camera_yaw_angle = 0
        self.camera_pitch_angle = 0
        self.camera_angle_amount = 1
        
        self.setup() 

    def setup(self):
        """Load assets and initialize properties."""
        self.data_points = self.load_assets(data_points_path, dtype="float")
        self.data_connections = self.load_assets(data_connections_path, dtype="int")
        self.data_connections_matrix = self.get_connection_matrix(self.data_connections)
        self.homogen_coords = self.get_homogen_coords(self.data_points)

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
    def yaw_cam(self, dir):
        if dir not in ["left","right"]:
            raise ValueError("Must be 'right' or 'left' for 'dir'.")
        
        if dir == "left":
            self.camera_pitch_angle += self.camera_angle_amount
        elif dir == "right":
            self.camera_pitch_angle -= self.camera_angle_amount
    
    def pitch_cam(self, dir):
        if dir not in ["up","down"]:
            raise ValueError("Must be 'up' or 'down' for 'dir'.")
        
        if dir == "up":
            self.camera_yaw_angle += self.camera_angle_amount
            if self.camera_yaw_angle > 90:
                print("Max pitch reached")
                self.camera_yaw_angle = 90
                return
            
        elif dir == "down":
            self.camera_yaw_angle -= self.camera_angle_amount
            if self.camera_yaw_angle < -90:
                print("Min pitch reached")
                self.camera_yaw_angle = -90
                return

    def update_cam(self):
        
        pitch_rad = np.radians(self.camera_pitch_angle)
        yaw_rad = np.radians(self.camera_yaw_angle)
        
        x = np.cos(pitch_rad)*np.sin(yaw_rad)
        y = np.sin(pitch_rad)
        z = np.cos(pitch_rad) * np.cos(yaw_rad)
        
        
        self.camera_direction[:] = x,y,z
        print(self.camera_direction)
        #print(self.camera_direction, self.camera_yaw_angle, self.camera_pitch_angle)

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
        self.screen.blit(pg.transform.scale(self.screen, self.WINDOW_DIM), (0, 0))

        self.update_cam()
        
        pg.draw.line(self.screen, "red", (0,0), (100,100), 3)
        pg.display.update()
        
        
        self.clock.tick(self.fps)

    def run(self):
        """Main game loop."""
        while True:
            self.handle_events()
            self.draw()

   
if __name__ == "__main__":
    game = Engine()
    game.run()