
import sys
import pygame as pg
import numpy as np
import os
import utils.helper_functions as helper_functions
import time
from object_classes.projectile import Projectile
from object_classes.tank import Tank
from object_classes.obstacle import Obstacle

class TankGame:
    def __init__(self):
        # Initialize Pygame
        pg.init()
        self.clock = pg.time.Clock()
        self.fps = 60

        # Window setup
        #self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1320, 580
        self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1980, 1200
        self.SCALE = 30
        self.screen = pg.display.set_mode(self.WINDOW_DIM)
        self.WINDOW_DIM_SCALED = self.WINDOW_W_SCALED, self.WINDOW_H_SCALED = int(self.WINDOW_W / (self.SCALE * 1.5)), int(self.WINDOW_H / self.SCALE)
        self.display = pg.Surface(self.WINDOW_DIM_SCALED)

        # Font
        self.font = pg.font.SysFont("monospace", 16)

        # Game objects
        self.units: list[Tank] = []
        self.projectiles: list[Projectile] = []
        self.obstacles: list[Obstacle] = []

        # Load assets
        self.load_assets()

        # Initialize game objectsd
        self.init_game_objects()

        # FPS tracking
        self.last_time = time.time()
        self.frame_count = 0
        self.current_fps = self.fps

    def load_assets(self):
        """Load and scale game assets (e.g., images)."""
        try:
            path_tank = os.path.join(os.getcwd(), "pictures", "tank2.png")
            path_tank_death = os.path.join(os.getcwd(), "pictures", "tank_death.png")

            self.tank_img = pg.image.load(path_tank).convert_alpha()
            self.tank_img = pg.transform.scale(self.tank_img, self.WINDOW_DIM_SCALED)

            self.tank_death_img = pg.image.load(path_tank_death).convert_alpha()
            self.tank_death_img = pg.transform.scale(self.tank_death_img, self.WINDOW_DIM_SCALED)
        except FileNotFoundError:
            print("Error: Image not found! Check your path.")
            sys.exit()

    def init_game_objects(self):
        """Initialize tanks and obstacles."""
        speed = 144 / self.fps        # 144 is just a const based on the speed i first tested game at
        firerate = 2
        speed_projectile = 2
        speed_projectile *= speed
        spawn_point  = (500, 500)
        player_tank = Tank(spawn_point, (0, 0), speed, firerate, speed_projectile, self.tank_img, self.tank_death_img)
        self.units.append(player_tank)

        # Map data i a tuple, where 1 entre is the polygon defining the map border the second is a list of all polygon cornerlists
        map_name = r"map_files\map_test1.txt"
        map_data = helper_functions.load_map_data(map_name)
        
        # Add bord
        self.obstacles.extend([Obstacle(map_data[0])])
                
        for polygon_conrners in map_data[1]:
            self.obstacles.extend([Obstacle(polygon_conrners)])

    def handle_events(self):
        """Handle player inputs and game events."""
        keys = pg.key.get_pressed()
        if keys[pg.K_q]:
            pg.quit()
            sys.exit()
        if keys[pg.K_a]:
            self.units[0].rotate(-1)
        if keys[pg.K_d]:
            self.units[0].rotate(1)
        if keys[pg.K_w]:
            self.units[0].move("forward")
        if keys[pg.K_s]:
            self.units[0].move("backward")
        if keys[pg.K_SPACE]:
            self.units[0].shoot()

        for e in pg.event.get():
            match e.type:
                case pg.QUIT:
                    pg.quit()
                    sys.exit()
                case pg.KEYDOWN:
                    if e.key == pg.K_r:
                        print("RESPAWN")
                        self.units[0].respawn()

    def update(self):
        
        # Temp list is created and all units projectiles are added to a single list
        temp_projectiles= []
        for unit in self.units:
            # Add projectiles from this unit to the list
            temp_projectiles.extend(unit.get_projectile_list())
            
        # The temp list is all active projetiles
        self.projectiles = temp_projectiles
        
        """Update game state: projectiles, units, and collisions."""
        # Update all projectiles from all tanks
        for unit in self.units:
            for i, proj in enumerate(unit.get_projectile_list()):
                for obstacle in self.obstacles:
                    for corner_pair in obstacle.get_corner_pairs():
                        proj.collision(corner_pair)

                projectile_line = proj.get_line()
                for unit in self.units:
                    if unit.collision(projectile_line, collision_type="projectile"):
                        unit.projectiles.pop(i)

                proj.update()

        # Remove dead projectiles
        self.projectiles[:] = [p for p in self.projectiles if p.alive]

        # Check unit collisions
        for unit in self.units:
            for obstacle in self.obstacles:
                for corner_pair in obstacle.get_corner_pairs():
                    unit.collision(corner_pair, collision_type="surface")

    def draw(self):
        """Render all objects on the screen."""
        self.display.fill("white")
        self.screen.blit(pg.transform.scale(self.display, self.WINDOW_DIM), (0, 0))

        for unit in self.units:
            unit.draw(self.screen)
        
        for proj in self.projectiles:
            proj.draw(self.screen)

        for obstacle in self.obstacles:
            # Debug: draw obstacle collision lines
            for corner_pair in obstacle.get_corner_pairs():
                pg.draw.line(self.screen, "red", corner_pair[0], corner_pair[1], 3)

        self.render_debug_info()

        pg.display.update()
        self.clock.tick(self.fps)

    def run(self):
        """Main game loop."""
        while True:
            self.handle_events()
            self.update()
            self.draw()
            
    def render_debug_info(self):
        """Render debug information on the right-side bar."""
        font = pg.font.Font(None, 24)  # Default font, size 24
        debug_text = [
            f"FPS: {self.clock.get_fps():.2f}",
            f"Active projectiles: {len(self.projectiles)}",
            f"Main tank angle: {self.units[0].degrees}"
        ]

        # Start position for text
        x_start = self.WINDOW_DIM[0] - 190  
        y_start = 10  

        for text in debug_text:
            text_surface = font.render(text, True, (0, 0, 0))  # White text
            self.screen.blit(text_surface, (x_start, y_start))
            y_start += 25  # Spacing between lines
            
