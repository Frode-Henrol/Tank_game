import pygame as pg
import utils.deflect as df
from object_classes.projectile import Projectile
import utils.helper_functions as helper_functions
import numpy as np
import random


class Tank:
    def __init__(self, 
                 startpos: tuple,
                 speed: float,
                 firerate: float,
                 speed_projectile: float,
                 spawn_degress: int,
                 bounch_limit: int, 
                 bomb_limit: int,
                 image, 
                 death_image,
                 use_turret,
                 ai_type = None):
        
        self.pos = list(startpos)
        self.direction = (0,0)  # Skal rettes
        self.degrees = spawn_degress
        self.speed = speed  # Used to control speed so it wont be fps bound
        
        # Projectile
        self.speed_projectile = speed_projectile # Scale the tanks projectile speed
        self.bounch_limit = bounch_limit
        
        # Bombs (not implemented)
        self.bomb_limit = bomb_limit

        self.current_speed = [0,0]
        self.firerate = firerate
        self.cannon_cooldown = 0
        self.init_hitbox(spawn_degress)    # Init the hitbox in the correct orientation
        self.dead = False
        self.godmode = False     # Toggle godmode for all tanks
        
        # Tank images:
        self.image = image
        self.death_image = death_image
        self.active_image = image
        
        # Projectiles from current tank
        self.projectiles: list[Projectile] = []
        
        # Use turret?
        self.use_turret = use_turret
        
        # AI
        # TEST DIC
        
        self.ai = TankAI(self, None) if ai_type else None
        
    def init_hitbox(self, spawn_degress):
        x = self.pos[0]
        y = self.pos[1]
        size_factor = 20
        # top left, top right, bottom right, bottom left ->  Front, right, back, right (line orientation in respect to tank, when run through coord_to_coordlist function)
        self.hitbox = [(x-size_factor, y-size_factor),
                       (x+size_factor, y-size_factor),
                       (x+size_factor, y+size_factor),
                       (x-size_factor, y+size_factor)]
        
        self.rotate_hit_box(spawn_degress)
        
    def move(self, direction: str):
        if self.dead and not self.godmode:
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
        
        # TEMP: constant to make sure tank image points right way
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
                
                if corner_pair == (self.hitbox[1], self.hitbox[2]):                     # Skal rettes! - lav front hitbox linje rød
                    pg.draw.line(surface, "green", corner_pair[0], corner_pair[1], 3)
        
        # Remove dead projectiles
        self.projectiles[:] = [p for p in self.projectiles if p.alive]
        
        #AI
        if self.ai:
            self.ai.update(States.IDLE)
    
    def rotate(self, deg: int):
        if self.dead and not self.godmode:
            return
        
        # Scale rotation to match speed
        deg *= self.speed
        
        # Rotate tank image
        self.degrees += deg
        rads = np.radians(self.degrees)
        
        # Update direction vector
        self.direction = np.cos(rads), np.sin(rads)
        
        # When rotating we also rate the tank hitbox
        self.rotate_hit_box(deg)

            
    def rotate_hit_box(self, deg):
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
        
        if active and not self.godmode:
            print("Tank dead")
            self.dead = True
            self.active_image = self.death_image
        else:
            self.dead = False
            self.active_image = self.image
               
    def shoot(self):
        if self.dead and not self.godmode:
            return
        if self.cannon_cooldown == 0:
            
            # At the moment the distance is hard coded, IT must be bigger than hit box or tank will shot itself.
            spawn_distance_from_middle = 30
            
            if self.use_turret:
                
                # Find the unit vector between mouse and tank. This is the projectile unit direction vector
                mouse_pos = pg.mouse.get_pos()
                unit_direction = helper_functions.unit_vector(self.pos, mouse_pos)
                projectile_direction = unit_direction
                
                print(f"{mouse_pos=} {unit_direction=}")
            else:
                # Calculate magnitude scalar of units direction vector
                magnitude_dir_vec = helper_functions.get_vector_magnitude(self.direction)
                
                # Find unit vector for direction
                unit_direction = (self.direction[0]/magnitude_dir_vec, self.direction[1]/magnitude_dir_vec)
                
                projectile_direction = self.direction
                    
            # Find position for spawn of projectile
            spawn_projectile_pos = [self.pos[0] + unit_direction[0]*spawn_distance_from_middle, self.pos[1] + unit_direction[1]*spawn_distance_from_middle]

            projectile = Projectile(spawn_projectile_pos, projectile_direction, speed=self.speed_projectile, bounce_limit=self.bounch_limit)
            self.projectiles.append(projectile)                                                                      
            print(self.direction)

        # Firerate is now just a cooldown amount
        self.cannon_cooldown = self.firerate

    def get_projectile_list(self):
        return self.projectiles
    
    def remove_projectile(self, index):
        pass
    
    def get_pos(self):
        return self.pos

    def get_hitbox_corner_pairs(self):
        return helper_functions.coord_to_coordlist(self.hitbox)
    
    def get_hitbox_front_pair(self):
        return self.hitbox[0], self.hitbox[1]
    
    def get_ai(self):
        return self.ai
    
    def add_direction_vector(self, vec_dir):
        # SKAL RETTES - meget logic burde kunne overføres til move method
        x1, y1 = vec_dir
        x2, y2 = self.pos 
        self.pos = list((x1+x2, y1+y2))
        
        # Move hit box:
        for i in range(len(self.hitbox)):
            x, y = self.hitbox[i]  # Unpack the point
            
            moved_x = x + x1
            moved_y = y + y1
            self.hitbox[i] = (moved_x, moved_y)
        
    def get_death_status(self):
        return self.dead

    def get_direction_vector(self):
        return self.direction
    


class TankAI:
    def __init__(self, tank: Tank, personality):
        self.tank = tank  # The tank instance this AI controls
        self.personality = personality
        self.state = "idle"  # Default state
        self.target = None  # Target for attack/movement

    def update(self, game_state):
        """Update AI behavior based on state."""
        if self.state ==  States.IDLE:
            self.idle_behavior()
        elif self.state == States.PATROLLING:
            self.patrol_behavior()
        elif self.state == States.CHASING:
            self.chase_behavior()
        elif self.state == States.ATTACKING:
            self.attack_behavior()
    
    def idle_behavior(self):
        """Do nothing or look around."""
        
        # Test:
        test = False
        if test:
            self.tank.rotate(random.randint(-1,2))
            
            self.tank.move("forward")
            
            if random.randint(0,1000) == 1:
                self.tank.shoot()
            
        pass

    def patrol_behavior(self):
        """Move around randomly or along a set path."""
        pass

    def chase_behavior(self):
        """Move toward the player or target."""
        pass

    def attack_behavior(self):
        """Shoot at the player or another enemy."""
        self.tank.shoot()

    def change_state(self, new_state):
        """Change the AI state."""
        self.state = new_state

class States:
    IDLE = "idle"
    PATROLLING = "patrolling"
    CHASING = "chasing"
    ATTACKING = "attacking"
    