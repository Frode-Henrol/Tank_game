
import pygame as pg
import utils.deflect as df
import copy
import random
from object_classes.animation import Animation

class Projectile:
    
    def __init__(self, startpos: tuple, direction: tuple, speed: list[float], bounce_limit: int):   # Add color and more later!!!!
        self.startpos = startpos
        self.pos = copy.copy(startpos)
        self.direction = direction
        self.degrees = 0
        self.speed_original = speed
        self.speed = speed  
        self.alive = True  
        self.lifespan = 5000     # Projectile lifespan
        self.thickness = 5
        self.set_visuals()
        
        self.bounce_count = 0
        self.bounce_limit = bounce_limit
        
        self.spawn_timer = 60
        self.hit_timer_amount = 0 # Frames. (0 right now which means maximum amount of collision checks)
        self.hit_timer = 0
    
    def set_visuals(self):
        t = (self.speed_original - 3.36) / (9.6 - 3.36)
        
        if t > 1: 
            t = 1
        elif t < 0: 
            t = 0
        
        self.color = (128 + 100*t, 128 - (128*t), 128 - (128*t)) 
        self.projectile_path_scale = 10 + 10 * t    # Scale of projectile len
    
    def set_delta_time(self, delta_time):
        self.delta_time = delta_time
        self.update_speed()
        
    def update_speed(self):
        self.speed = self.speed_original * self.delta_time * 60
    
    def init_sound_effects(self, sound_effects):
        self.sound_effects = sound_effects
        
        self.hit_sounds = sound_effects[9:13]
        self.projexp_sounds = self.sound_effects[13:19]
    
    def update(self):
        
        # Update projectile speed based on framerate
        self.update_speed() 
        
        # Hit timer to control how often to do collision checks
        if self.hit_timer > 0:
            self.hit_timer -= 1
        
        # Update position of projectile
        self.pos[0] += self.direction[0]*self.speed
        self.pos[1] += self.direction[1]*self.speed
        
        # Update spawn timer (UNUSED)
        if self.spawn_timer > 0:
            self.spawn_timer -= 1
        
        # Update lifespan timer
        self.lifespan -= self.delta_time * 60
        if self.lifespan <= 0:
            self.alive = False
        
        # Check if max bounces is reached
        if self.bounce_count >= self.bounce_limit:
            self.play_explosion()
            self.alive = False
    
    def play_explosion(self):
        # Play projectile explosion animation if active
        random.choice(self.projexp_sounds).play()
        
    def get_pos(self):
        return self.pos
    
    def get_dir(self):
        return self.direction
    
    def get_line(self):
        return [(self.pos[0], self.pos[1]), (self.pos[0]+self.direction[0]*self.projectile_path_scale, self.pos[1]+self.direction[1]*self.projectile_path_scale)]
        
    def draw(self, surface):
        #pg.draw.circle(surface, "red", (int(self.pos[0]), int(self.pos[1])), 2)
        line_start, line_end = self.get_line()
        pg.draw.line(surface, self.color, (line_start[0], line_start[1]), (line_end[0], line_end[1]), self.thickness)
        
        
    def collision(self, line):
        """line should be a tuple of 2 coords"""
        if self.hit_timer > 0:
            return
        
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
        if intersect_coord == (-1.0, -1.0):
            return self.direction
        
        self.startpos = intersect_coord     # Update startpos for ai dodge mechanic
        
        # Find normal vector of line
        normal_vector1, normal_vector2 = df.find_normal_vectors(line_coord1, line_coord2)
        # print(f"Line start: {line_coord1}   End: {line_coord2}")
        
        # Find deflection vector and update the direction vector
        
        dot1 = normal_vector1[0]*self.direction[0] + normal_vector1[1]*self.direction[1]
        dot2 = normal_vector2[0]*self.direction[0] + normal_vector2[1]*self.direction[1]

        # The dot product should be negative if it is facing the projectile.   (Lige pt virker det ligemeget hvilken normalvector der vælges)
        if dot1 < 0:
            chosen_normal = normal_vector1
        else:
            chosen_normal = normal_vector2
            
        self.direction = df.find_deflect_vector(chosen_normal, self.direction)
        random.choice(self.hit_sounds).play()   # Choose random sound
        
        self.bounce_count +=1
        self.hit_timer = self.hit_timer_amount
        
    def add_bounce_count(self): 
        self.bounce_count += 1
    
    def get_bounce_count(self):
        return self.bounce_count
    
    def get_pos(self):
        return self.pos
    
    def set_alive(self, state: bool):
        self.alive = state
    
    def __repr__(self):
        return f"Dir vector: ({float(self.pos[0]):.1f}, {float(self.pos[1]):.1f})"