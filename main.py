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

projectiles = []
obstacles = []

# MAIN LOOP
def main():
    path_tank = os.path.join(os.getcwd(),"pictures","tank2.png")
    
    try:
        tank_img = pg.image.load(path_tank).convert_alpha()  # Convert for performance
        tank_img = pg.transform.scale(tank_img, (DW, DH))  # Scale image to match display
    except FileNotFoundError:
        print("Error: Image not found! Check your path.")
        sys.exit()
            
    # Init player tank
    speed = 1
    firerate = 1
    player_tank = Tank((100,500), (0,0), speed, firerate, tank_img)
    k = 400
    test_rect = Obstacle([(100+k,100+k),(400+k,100+k),(400+k,250+k),(100+k,250+k)])
    test_rect2 = Obstacle([(20+k,20+k),(80+k,20+k),(80+k,50+k),(20+k,50+k)])
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
        

        # Update projectiles: for each projectile, check all obstacles before updating
        for proj in projectiles:
            for obstacle in obstacles:
                corner_pairs = obstacle.get_corner_pairs()
                for corner_pair in corner_pairs:
                    proj.collision(corner_pair)
            proj.update()
            
            #pos = proj.get_pos()
            #print(f"{pos[0]:.1f}, {pos[1]:.1f}")
            
        # Remove dead projectiles
        projectiles[:] = [p for p in projectiles if p.alive]
        
        # Draw entities
        player_tank.draw(screen)
            
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
    def __init__(self, startpos: tuple, direction: tuple, speed: float, firerate: float, image):
        self.pos = list(startpos)
        self.direction = direction
        self.degrees = 0
        self.speed = speed
        self.image = image
        self.current_speed = [0,0]
        self.firerate = firerate
        self.cannon_cooldown = 0
        
        
    def move(self, direction: str):
        if direction == "forward":
            self.pos[0] += self.direction[0]*self.speed
            self.pos[1] += self.direction[1]*self.speed
            
        elif direction == "backward":
            self.pos[0] -= self.direction[0]*self.speed
            self.pos[1] -= self.direction[1]*self.speed
        
        #print(self.pos)
    
    def draw(self, surface):
        # TEMP: constant to make sure tank points right way
        tank_correct_orient = -90
        rotated_image = pg.transform.rotate(self.image, -self.degrees+tank_correct_orient)
        rect = rotated_image.get_rect(center=self.pos)
        surface.blit(rotated_image, rect.topleft)
        
        # Decrease cooldown each new draw
        if self.cannon_cooldown > 0:
            self.cannon_cooldown -= 1

    def rotate(self, deg: int):
        self.degrees += deg
        rads = np.radians(self.degrees)
        self.direction = np.cos(rads), np.sin(rads)
        #print(f"Rotation: {self.degrees}°, Direction: {self.direction}")
        
    def collision(self):
        # TODO
        pass
    
    def shoot(self):
        if self.cannon_cooldown == 0:
            projectile = Projectile(self.pos[:], self.direction, speed=0.3)
            projectiles.append(projectile)
            print(projectile)
        
        # Firerate is now just a cooldown amount
        self.cannon_cooldown = self.firerate
    
    
class Projectile:
    
    def __init__(self, startpos: tuple, direction: tuple, speed: int):
        self.pos = startpos
        self.direction = direction
        self.degrees = 0
        self.speed = speed
        self.lifespan = 500
        self.alive = True
        
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
        
    def draw(self, surface):
        pg.draw.circle(surface, "red", (int(self.pos[0]), int(self.pos[1])), 2)
        
    def collision(self, line):
        """line should be a tuple of 2 coords"""
        
        # Coords of the "surface" line in the polygon
        line_coord1, line_coord2 = line
        
        # Start of projectile path in a given frame
        start_point = self.pos
        # End of projectile path in a given frame
        
        end_point = (self.pos[0] + self.direction[0] * self.speed*1,
                    self.pos[1] + self.direction[1] * self.speed*1)
        
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
    
    
def coord_to_coordlist(coordinat_list):
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





if __name__ == "__main__":
    main()