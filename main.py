import sys
import pygame as pg
import numpy as np
import os
import deflect as df
import helper_functions
import time
import random


class TankGame:
    def __init__(self):
        # Initialize Pygame
        pg.init()
        self.clock = pg.time.Clock()
        self.fps = 60

        # Window setup
        self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1000, 1000
        self.SCALE = 20
        self.screen = pg.display.set_mode(self.WINDOW_DIM)
        self.WINDOW_DIM_SCALED = self.WINDOW_W_SCALED, self.WINDOW_H_SCALED = int(self.WINDOW_W / self.SCALE), int(self.WINDOW_H / self.SCALE)
        self.display = pg.Surface(self.WINDOW_DIM_SCALED)

        # Font
        self.font = pg.font.SysFont("monospace", 16)

        # Game objects
        self.units: list[Tank] = []
        self.projectiles: list[Projectile] = []
        self.obstacles: list[Obstacle] = []

        # Load assets
        self.load_assets()

        # Initialize game objects
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
        player_tank = Tank((100, 500), (0, 0), speed, firerate, speed_projectile, self.tank_img, self.tank_death_img)
        self.units.append(player_tank)

        k, j = 400, 200
        self.obstacles.extend([
            Obstacle([(100+k, 100+k), (400+k, 100+k), (400+k, 250+k), (100+k, 250+k)]),
            Obstacle([(20+k, 20+k), (80+k, 20+k), (80+k, 50+k), (20+k, 50+k)]),
            Obstacle([(0, 0), (0, 998), (998, 998), (998, 0)]),
            Obstacle([(10+j, 0), (80+j, 20+j), (80+j, 50+j), (20+j, 50+j)])
        ])

        print(helper_functions.coord_to_coordlist([(20+k, 20+k), (80+k, 20+k), (80+k, 50+k), (20+k, 50+k)]))

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

        # UI text
        self.screen.blit(self.font.render(f"Active projectiles {len(self.projectiles)}", 1, (0, 0, 0)), (5, 480))
        
        # Calculate and display FPS
        current_time = time.time()
        self.frame_count += 1
        if current_time - self.last_time >= 1:  # Once every second
            self.current_fps = self.frame_count
            self.frame_count = 0
            self.last_time = current_time
            # Display FPS on screen
        
        self.screen.blit(self.font.render(f"FPS: {self.current_fps}", 1, (0, 0, 0)), (5, 580))


        pg.display.update()
        self.clock.tick(self.fps)

    def run(self):
        """Main game loop."""
        while True:
            self.handle_events()
            self.update()
            self.draw()
            
class Tank:
    def __init__(self, startpos: tuple, direction: tuple, speed: float, firerate: float, speed_projectile: float, image, death_image):
        self.pos = list(startpos)
        self.direction = direction
        self.degrees = 0
        self.speed = speed  # Used to control speed so it wont be fps bound
        self.speed_projectile = speed_projectile # Scale the tanks projectile speed
        self.image = image
        self.death_image = death_image
        self.active_image = image
        self.current_speed = [0,0]
        self.firerate = firerate
        self.cannon_cooldown = 0
        self.hitbox = self.init_hitbox()
        self.dead = False
        
        self.projectiles: list[Projectile] = []
        
        
    def init_hitbox(self):
        x = self.pos[0]
        y = self.pos[1]
        size_factor = 20
        # top left, top right, bottom right, bottom left ->  Front, right, back, right (line orientation in respect to tank, when run through coord_to_coordlist function)
        return [(x-size_factor, y-size_factor),
                (x+size_factor, y-size_factor),
                (x+size_factor, y+size_factor),
                (x-size_factor, y+size_factor)]
        
    def move(self, direction: str):
        if self.dead:
            return
            
        if direction == "forward":
            dir = 1
        elif direction == "backward":
            dir = -1
        
        # Move tank image
        self.pos[0] = self.pos[0] + dir * self.direction[0] * self.speed
        self.pos[1] = self.pos[1] + dir * self.direction[1] * self.speed
        
        # Move hit box:
        for i in range(len(self.hitbox)):
            x, y = self.hitbox[i]  # Unpack the point
            
            moved_x = x + dir * self.direction[0] * self.speed
            moved_y = y + dir * self.direction[1] * self.speed
            self.hitbox[i] = (moved_x, moved_y)
    
    def respawn(self):
        self.make_dead(False)
    
    def draw(self, surface):
        
        # TEMP: constant to make sure tank points right way
        tank_correct_orient = -90
        rotated_image = pg.transform.rotate(self.active_image, -self.degrees+tank_correct_orient)
        rect = rotated_image.get_rect(center=self.pos)
        surface.blit(rotated_image, rect.topleft)
        
        # Decrease cooldown each new draw
        if self.cannon_cooldown > 0:
            self.cannon_cooldown -= 1
        
        #Update hitbox:
        draw_hitbox = True 
        if draw_hitbox:
            for corner_pair in helper_functions.coord_to_coordlist(self.hitbox):
                pg.draw.line(surface, "blue", corner_pair[0], corner_pair[1], 3)

        # Remove dead projectiles
        self.projectiles[:] = [p for p in self.projectiles if p.alive]
    
    def rotate(self, deg: int):
        if self.dead:
            return
        
        # Scale rotation to match speed
        deg *= self.speed
        
        # Rotate tank image
        self.degrees += deg
        rads = np.radians(self.degrees)
        
        # Update direction vector
        self.direction = np.cos(rads), np.sin(rads)
        #print(f"Rotation: {self.degrees}°, Direction: {self.direction}")
        
        # Rotate tank hitbox
        rads = np.radians(deg)  # The hitbox is rotated specified degress
        
        # Rotate all 4 corners in the hitbox
        for i in range(len(self.hitbox)):
            x, y = self.hitbox[i]
            
            # Corrected 2D rotation formulawa
            rotated_x = self.pos[0] + (x - self.pos[0]) * np.cos(rads) - (y - self.pos[1]) * np.sin(rads)
            rotated_y = self.pos[1] + (x - self.pos[0]) * np.sin(rads) + (y - self.pos[1]) * np.cos(rads)

            # Update the list in place
            self.hitbox[i] = (rotated_x, rotated_y)

    def collision(self, line: tuple, collision_type: str) -> bool:
        """line should be a tuple of 2 coords"""
        
        # Coords of the "surface" line in the polygon
        line_coord1, line_coord2 = line
        
        # Find coord where tank and line meet. Try all 4 side of tank
        hit_box_lines = helper_functions.coord_to_coordlist(self.hitbox)
        
        # Check each line in hitbox if it itersect a line: surface/projectile/etc
        for i in range(len(hit_box_lines)):
            start_point, end_point = hit_box_lines[i]
            intersect_coord = df.line_intersection(line_coord1, line_coord2, start_point, end_point)
        
            # Only execute code when a collision is present. The code under will push the tank back with the normal vector to the line "surface" hit (with same magnitude as unit direction vector)
            if intersect_coord != None:
                print(f"Tank hit line at coord: ({float(intersect_coord[0]):.1f},  {float(intersect_coord[1]):.1f})")
                
                # If collision is a ____
                if collision_type == "surface":
                    # Find normal vector of line
                    normal_vector1, normal_vector2 = df.find_normal_vectors(line_coord1, line_coord2)
                    # - We only use normalvector2 since all the left sides of the hitbox lines point outwards
                    
                    # Calculate magnitude scalar of units direction vector
                    magnitude_dir_vec = helper_functions.get_vector_magnitude(self.direction) 
                    
                    # Scale the normal vector with the previous magnitude scalar
                    normal_scaled_x, normal_scaled_y = normal_vector2[0] * magnitude_dir_vec, normal_vector2[1] * magnitude_dir_vec
                    
                    self.rotate(random.randint(-1,1)) #-----------------------------------------------------------------------------------------Crappy fix that makes tank wobble when hitting wall, making clipping harder DELETE THIS
                    
                    # Update unit postion
                    self.pos = [self.pos[0] + normal_scaled_x * self.speed, self.pos[1] + normal_scaled_y * self.speed]
                    
                    # Update each corner position in hitbox
                    for i in range(len(self.hitbox)):
                        x, y = self.hitbox[i]
                        self.hitbox[i] = (x + normal_scaled_x * self.speed, y + normal_scaled_y * self.speed)
                        
                        
                elif collision_type == "projectile":
                    self.make_dead(True)
                    return True
                else:
                    print("Hitbox collision: type is unknown")
        
    def make_dead(self, active):
        
        if active:
            print("Tank dead")
            self.dead = True
            self.active_image = self.death_image
        else:
            self.dead = False
            self.active_image = self.image
               
    def shoot(self):
        if self.dead:
            return
        if self.cannon_cooldown == 0:
            
            # At the moment the distance is hard coded, IT must be bigger than hit box or tank will shot itself.
            spawn_distance_from_middle = 25
            
            # Calculate magnitude scalar of units direction vector
            magnitude_dir_vec = helper_functions.get_vector_magnitude(self.direction)
            
            # Find unit vector for direction
            unit_diretion = (self.direction[0]/magnitude_dir_vec, self.direction[1]/magnitude_dir_vec)
            
            # Find position for spawn of projectile
            spawn_projectile_pos = [self.pos[0] + unit_diretion[0]*spawn_distance_from_middle, self.pos[1] + unit_diretion[1]*spawn_distance_from_middle]
        
            #
            projectile = Projectile(spawn_projectile_pos, self.direction, speed=self.speed_projectile)
            self.projectiles.append(projectile)                                                                      # --------------- Class should have own list of the projectiles, and main should go throug each units projectiles 
            print(projectile)

        # Firerate is now just a cooldown amount
        self.cannon_cooldown = self.firerate

    def get_projectile_list(self):
        return self.projectiles
    
    def remove_projectile(self, index):
        pass
 
class Projectile:
    
    def __init__(self, startpos: tuple, direction: tuple, speed: int):
        self.pos = startpos
        self.direction = direction
        self.degrees = 0
        self.speed = speed  # Speed is ju
        self.alive = True  
        self.lifespan = 500     # Projectile lifespan
        self.projectile_path_scale = 10     # Scale of projectile len
        
    def update(self):
        self.pos[0] += self.direction[0]*self.speed
        self.pos[1] += self.direction[1]*self.speed
        
        self.lifespan -= 1
        
        if self.lifespan <= 0:
            self.alive = False
            
    def get_pos(self):
        return self.pos
    
    def get_dir(self):
        return self.direction
    
    def get_line(self):
        return [(self.pos[0], self.pos[1]), (self.pos[0]+self.direction[0]*self.projectile_path_scale, self.pos[1]+self.direction[1]*self.projectile_path_scale)]
        
    def draw(self, surface):
        #pg.draw.circle(surface, "red", (int(self.pos[0]), int(self.pos[1])), 2)
        line_start, line_end = self.get_line()
        pg.draw.line(surface, "blue", (line_start[0], line_start[1]), (line_end[0], line_end[1]), 3)
        
    def collision(self, line):
        """line should be a tuple of 2 coords"""
        
        # Coords of the "surface" line in the polygon
        line_coord1, line_coord2 = line
        
        # Start of projectile path in a given frame
        start_point = self.pos
        # End of projectile path in a given frame
        
        end_point = (self.pos[0] + self.direction[0] * self.projectile_path_scale,
                    self.pos[1] + self.direction[1] * self.projectile_path_scale)
        
        # Find coord where projectile and line meet
        intersect_coord = df.line_intersection(line_coord1, line_coord2, start_point, end_point)
 
        # If there is no intersection then just keep diretion vector the same
        if intersect_coord == None:
            return self.direction
        
        print(f"Projectile hit line at coord: ({float(intersect_coord[0]):.1f},  {float(intersect_coord[1]):.1f})")
        print(f"Projectile has coord        : ({float(self.pos[0]):.1f},  {float(self.pos[1]):.1f})")
        
        # Find normal vector of line
        normal_vector1, normal_vector2 = df.find_normal_vectors(line_coord1, line_coord2)
        print(f"Line start: {line_coord1}   End: {line_coord2}")
        
        # Find deflection vector and update the direction vector
        
        dot1 = normal_vector1[0]*self.direction[0] + normal_vector1[1]*self.direction[1]
        dot2 = normal_vector2[0]*self.direction[0] + normal_vector2[1]*self.direction[1]

        # The dot product should be negative if it is facing the projectile.   (Lige pt virker det ligemeget hvilken normalvector der vælges)
        if dot1 < 0:
            chosen_normal = normal_vector1
        else:
            chosen_normal = normal_vector2

        print(f"dot1: {dot1:.1f} dot2: {dot2:.1f} Chosen: {dot1:.1f}")
        print(f"New direction after reflection: {self.direction[0]:.2f}, {self.direction[1]:.2f}")
        # Now do the reflection/deflection with chosen_normal
        self.direction = df.find_deflect_vector(chosen_normal, self.direction)
    
    def __repr__(self):
        return f"Dir vector: ({float(self.pos[0]):.1f}, {float(self.pos[1]):.1f})"
    
class Obstacle:
    
    def __init__(self, corners_list):
        self.corners = corners_list
        
    def draw(self, surface):    
        pg.draw.polygon(surface, "black", self.corners) 
        
    def get_corner_pairs(self):
        # Convert the polygon corners to pairs representing each line in the polygon
        return helper_functions.coord_to_coordlist(self.corners)
    


if __name__ == "__main__":
    game = TankGame()
    game.run()