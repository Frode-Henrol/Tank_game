import sys
import pygame as pg
import numpy as np
import os
import csv

data_points_path = os.path.join(os.getcwd(),"Polygon_3D_model_test","data_points.txt")
data_connections_path = os.path.join(os.getcwd(),"Polygon_3D_model_test","data_connections.txt")

class Engine:
    def __init__(self):
        # Initialize Pygame
        pg.init()
        self.clock = pg.time.Clock()
        self.fps = 60

        # Window setup
        self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1920, 1080
        self.SCALE = 30
        self.screen = pg.display.set_mode(self.WINDOW_DIM)
        self.WINDOW_DIM_SCALED = self.WINDOW_W_SCALED, self.WINDOW_H_SCALED = int(self.WINDOW_W / (self.SCALE * 1.5)), int(self.WINDOW_H / self.SCALE)
        self.display = pg.Surface(self.WINDOW_DIM_SCALED)
        
        # Load all coords and the connections between them
        self.data_points = self.load_assets(data_points_path, type="float")
        self.data_connections = self.load_assets(data_connections_path, type = "int")
        self.data_connections_matrix = self.get_connection_matrix(self.data_connections)
        
        self.homogen_coords = self.get_homogen_coords()     # Create homogen matrix of zeros

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
        

    def get_homogen_coords(self):
        homogen_zero_matrix = np.zeros((len(self.polygon[0]) + 1,len(self.polygon)))[-1][:] = 1 # Create zero matrix and set last row to pure 1's
        
        # Add the data to the matrix
        for i in range(len(self.data)):
            homogen_zero_matrix[:3,i] = self.data[i]
        
        return homogen_zero_matrix
        
    def load_assets(self, filename: str, type: str):
        
        if type not in ["int","float"]:
            raise ValueError("Input type must be either 'int' or 'float'")
        
        with open(filename, "r", encoding="utf-8") as file:
            
            reader = csv.reader(file)
            
            if type == "float":
                data = [list(map(float, row)) for row in reader]
            if type == "int":
                data = [list(map(int, row)) for row in reader]
            
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
        

    def handle_events(self):
        """Handle player inputs and game events."""
        keys = pg.key.get_pressed()
        if keys[pg.K_q]:
            pg.quit()
            sys.exit()

        for e in pg.event.get():
            match e.type:
                case pg.QUIT:
                    pg.quit()
                    sys.exit()


    def draw(self):
        """Render all objects on the screen."""
        self.display.fill("white")
        self.screen.blit(pg.transform.scale(self.display, self.WINDOW_DIM), (0, 0))
        
        

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