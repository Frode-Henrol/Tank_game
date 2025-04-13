
import pygame as pg
import utils.deflect as df
import copy

class Projectile:
    
    def __init__(self, startpos: tuple, direction: tuple, speed: int, bounce_limit: int):   # Add color and more later!!!!
        self.startpos = startpos
        self.pos = copy.copy(startpos)
        self.direction = direction
        self.degrees = 0
        self.speed = speed  
        self.alive = True  
        self.lifespan = 50000     # Projectile lifespan
        self.projectile_path_scale = 10     # Scale of projectile len
        self.bounce_count = 0
        self.bounce_limit = bounce_limit
        
        self.spawn_timer = 60
        
    def update(self):
        self.pos[0] += self.direction[0]*self.speed
        self.pos[1] += self.direction[1]*self.speed
        
        self.lifespan -= 1
        if self.spawn_timer > 0:
            self.spawn_timer -= 1
        
        if self.lifespan <= 0:
            self.alive = False
            
        if self.bounce_count >= self.bounce_limit:
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
        pg.draw.line(surface, "grey", (line_start[0], line_start[1]), (line_end[0], line_end[1]), 6)
        
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
        
        self.startpos = intersect_coord     # Update startpos for ai dodge mechanic
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
            
        # SKAL SLETTES: (bare test med tvungen normalvektor)
        #chosen_normal =  normal_vector2

        print(f"dot1: {dot1:.1f} dot2: {dot2:.1f} Chosen: {dot1:.1f}")
        print(f"New direction after reflection: {self.direction[0]:.2f}, {self.direction[1]:.2f}")
        # Now do the reflection/deflection with chosen_normal
        self.direction = df.find_deflect_vector(chosen_normal, self.direction)
        
        self.bounce_count +=1
        
    def add_bounce_count(self): 
        self.bounce_count +=1       #SKAL SLETTES
    
    def get_bounce_count(self):
        return self.bounce_count
    
    def get_pos(self):
        return self.pos
    
    def set_alive(self, state: bool):
        self.alive = state
    
    def __repr__(self):
        return f"Dir vector: ({float(self.pos[0]):.1f}, {float(self.pos[1]):.1f})"