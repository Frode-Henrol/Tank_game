import sys
import pygame as pg
import numpy as np
import os
import deflect as df

# SETUP
pg.init()
clock = pg.time.Clock()
fps = 144
# WINDOW
WH = W, H = 1000, 1000
SCALE = 20
screen = pg.display.set_mode(WH)
DWH = DW, DH = int(W / SCALE), int(H / SCALE)
display = pg.Surface(DWH)
MID = MW, MH = [DW / 2, DH / 2]

# For text
myfont = pg.font.SysFont("monospace", 16)

units = []
projectiles = []
obstacles = []

# MAIN LOOP
def main():
    path_tank = os.path.join(os.getcwd(),"pictures","tank2.png")
    path_tank_death = os.path.join(os.getcwd(),"pictures","tank_death.png")
    
    try:
        tank_img = pg.image.load(path_tank).convert_alpha()  # Convert for performance
        tank_img = pg.transform.scale(tank_img, (DW, DH))  # Scale image to match display
        
        tank_death_img = pg.image.load(path_tank_death).convert_alpha()  # Convert for performance
        tank_death_img = pg.transform.scale(tank_death_img, (DW, DH))  # Scale image to match display
        
    except FileNotFoundError:
        print("Error: Image not found! Check your path.")
        sys.exit()
            
    # Init player tank
    speed = 1
    firerate = 2
    player_tank = Tank((100,500), (0,0), speed, firerate, tank_img, tank_death_img)
    units.append(player_tank)
    k = 400
    test_rect = Obstacle([(100+k,100+k),(400+k,100+k),(400+k,250+k),(100+k,250+k)])
    test_rect2 = Obstacle([(20+k,20+k),(80+k,20+k),(80+k,50+k),(20+k,50+k)])
    test_rect2 = Obstacle([(0,0),(0,998),(998,998),(998,0)])
    j = 200
    test_rect3 = Obstacle([(10+j,0),(80+j,20+j),(80+j,50+j),(20+j,50+j)])
    
    obstacles.append(test_rect)
    obstacles.append(test_rect2)
    obstacles.append(test_rect3)
    
    print(coord_to_coordlist([(20+k,20+k),(80+k,20+k),(80+k,50+k),(20+k,50+k)]))
    
    while True:
        display.fill("white")

        screen.blit(tank_img,(100,100))
               
      # EVENTS
        for e in pg.event.get():
            match e.type:
                case pg.QUIT:
                    pg.quit()
                    sys.exit()
                case pg.KEYDOWN:
                    if e.key == pg.K_q:
                        pg.quit()
                        sys.exit()
                    if e.key == pg.K_r:
                        print("RESPAWN")
                        player_tank.respawn()
                            
                
                
        # HANDLE KEY HOLDS
        keys = pg.key.get_pressed()
        if keys[pg.K_q]:
            pg.quit()
            sys.exit()
        if keys[pg.K_a]:
            player_tank.rotate(-1)
        if keys[pg.K_d]:
            player_tank.rotate(1)
        if keys[pg.K_w]:
            player_tank.move("forward")
        if keys[pg.K_s]:
            player_tank.move("backward")
        if keys[pg.K_SPACE]:
            player_tank.shoot() 

        screen.blit(pg.transform.scale(display, WH), (0, 0))
        

        # Update projectiles: for each projectile, check all obstacles before updating  -  Could be moved down to the other for loop with proj***
        for i, proj in enumerate(projectiles):
            for obstacle in obstacles:
                corner_pairs = obstacle.get_corner_pairs()
                for corner_pair in corner_pairs:
                    proj.collision(corner_pair)
            
            # Get projectile line
            projectile_line = proj.get_line() 
            
            # Check if projetile hits any unit - remove projectile if it hits tank
            for unit in units:
                is_hit = unit.collision(projectile_line, collision_type="projectile")
                if is_hit:
                    projectiles.pop(i)
                    
            proj.update()
                        
        # Remove dead projectiles
        projectiles[:] = [p for p in projectiles if p.alive]
        
        # Check for unit collision:
        
        # Draw entities
        for unit in units:
            for obstacle in obstacles:
                corner_pairs = obstacle.get_corner_pairs()
                for corner_pair in corner_pairs:
                    unit.collision(corner_pair, collision_type="surface")
        
            unit.draw(screen)
            
        for proj in projectiles:
            proj.draw(screen)
            
        for obstacle in obstacles:
            #obstacle.draw(screen)  ------------------------------------------------------------------------!! Turned of so we only see wireframe
            
            # !!!!! THIS is just for debug, and makes the lines visible:
            corner_pairs = obstacle.get_corner_pairs()
            for corner_pair in corner_pairs:
                pg.draw.line(screen, "red", corner_pair[0], corner_pair[1], 3)

        screen.blit(myfont.render(f"Active projectiles {len(projectiles)}", 1, (0,0,0)), (5, 480))
        screen.blit(myfont.render(f"FPS {fps}", 1, (0,0,0)), (5, 580))
        
        pg.display.update()
        clock.tick(fps)
        

class Tank:
    def __init__(self, startpos: tuple, direction: tuple, speed: float, firerate: float, image, death_image):
        self.pos = list(startpos)
        self.direction = direction
        self.degrees = 0
        self.speed = speed
        self.image = image
        self.death_image = death_image
        self.active_image = image
        self.current_speed = [0,0]
        self.firerate = firerate
        self.cannon_cooldown = 0
        self.hitbox = self.init_hitbox()
        self.dead = False
        
        
        
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
        self.pos[0] = self.pos[0] + dir * self.direction[0]*self.speed
        self.pos[1] = self.pos[1] + dir * self.direction[1]*self.speed
        
        # Move hit box:
        for i in range(len(self.hitbox)):
            x, y = self.hitbox[i]  # Unpack the point
            
            moved_x = x + dir * self.direction[0]
            moved_y = y + dir * self.direction[1]
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
        draw_hitbox = False 
        if draw_hitbox:
            for corner_pair in coord_to_coordlist(self.hitbox):
                pg.draw.line(screen, "blue", corner_pair[0], corner_pair[1], 3)

    def rotate(self, deg: int):
        if self.dead:
            return
        
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
        hit_box_lines = coord_to_coordlist(self.hitbox)
        
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
                    magnitude_dir_vec = get_vector_magnitude(self.direction) * 1.1
                    
                    # Scale the normal vector with the previous magnitude scalar
                    normal_scaled_x, normal_scaled_y = normal_vector2[0] * magnitude_dir_vec, normal_vector2[1] * magnitude_dir_vec
                    
                    # Update unit postion
                    self.pos = [self.pos[0]+normal_scaled_x, self.pos[1]+normal_scaled_y]
                    
                    # Update each corner position in hitbox
                    for i in range(len(self.hitbox)):
                        x, y = self.hitbox[i]
                        self.hitbox[i] = (x + normal_scaled_x, y + normal_scaled_y)
                    
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
            magnitude_dir_vec = get_vector_magnitude(self.direction)
            
            # Find unit vector for direction
            unit_diretion = (self.direction[0]/magnitude_dir_vec, self.direction[1]/magnitude_dir_vec)
            
            # Find position for spawn of projectile
            spawn_projectile_pos = [self.pos[0] + unit_diretion[0]*spawn_distance_from_middle, self.pos[1] + unit_diretion[1]*spawn_distance_from_middle]
        
            projectile = Projectile(spawn_projectile_pos, self.direction, speed=2)
            projectiles.append(projectile)                                                                      # --------------- Class should have own list of the projectiles, and main should go throug each units projectiles 
            print(projectile)

        # Firerate is now just a cooldown amount
        self.cannon_cooldown = self.firerate
    

class Projectile:
    
    def __init__(self, startpos: tuple, direction: tuple, speed: int):
        self.pos = startpos
        self.direction = direction
        self.degrees = 0
        self.speed = speed
        self.lifespan = 50000
        self.alive = True
        self.projectile_path_scale = 10
        
    def update(self):
        self.pos[0] += self.direction[0]*self.speed
        self.pos[1] += self.direction[1]*self.speed
        
        #self.pos[0] = round(self.pos[0], 5)
        #self.pos[1] = round(self.pos[1], 5)
        
        self.lifespan -= 1
        
        if self.lifespan <= 0:
            self.alive = False
            
    def get_pos(self):
        return self.pos
    
    def get_dir(self):
        return self.direction
    
    def get_line(self):
        return [(self.pos[0], self.pos[1]), (self.pos[0]+self.direction[0]*self.speed*self.projectile_path_scale, self.pos[1]+self.direction[1]*self.speed*self.projectile_path_scale)]
        
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
        
        end_point = (self.pos[0] + self.direction[0] * self.speed*self.projectile_path_scale,
                    self.pos[1] + self.direction[1] * self.speed*self.projectile_path_scale)
        
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
        return coord_to_coordlist(self.corners)
    
    
def coord_to_coordlist(coordinat_list: list) -> list:
    """Takes a list of coordinates (polygon) and makes tuples representing each line"""
    new_coordinat_list = []
    length = len(coordinat_list)

    # Connect polygon
    for i in range(length-1):
        new_coordinat_list.append((coordinat_list[i], coordinat_list[i+1]))
    
    # close the polygon
    new_coordinat_list.append((coordinat_list[-1], coordinat_list[0]))
    
    #return [((420, 420), (480, 420)),((400,100),(600,100))] #------------------------------------------------------------!
    return new_coordinat_list

def get_vector_magnitude(vector: list) -> float:
    return np.sqrt(vector[0] ** 2 + vector[1] ** 2)



if __name__ == "__main__":
    main()