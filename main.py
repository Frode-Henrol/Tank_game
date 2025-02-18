import sys
import pygame as pg
import numpy as np
import os

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
    player_tank = Tank((500,500), (0,0), speed, tank_img)
    test_rect = Obstacle([(50,50),(500,50),(100,100),(50,100)])
    
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
        
        # Update projectiles
        for proj in projectiles:
            proj.update()
            
        # Remove dead projectiles
        projectiles[:] = [p for p in projectiles if p.alive]
        
        # Draw entities
        player_tank.draw(screen)
        test_rect.draw(screen)
            
        for proj in projectiles:
            proj.draw(screen)
            
    
        screen.blit(myfont.render(f"Active projectiles {len(projectiles)}", 1, (0,0,0)), (5, 480))
        screen.blit(myfont.render(f"FPS {fps}", 1, (0,0,0)), (5, 580))
        
        pg.display.update()
        clock.tick(fps)
        

class Tank:
    def __init__(self, startpos: tuple, direction: tuple, speed: int, image):
        self.pos = list(startpos)
        self.direction = direction
        self.degrees = 0
        self.speed = speed
        self.image = image
        self.current_speed = [0,0]
        
        
    def move(self, direction: str):
        if direction == "forward":
            self.pos[0] += self.direction[0]*self.speed
            self.pos[1] += self.direction[1]*self.speed
            
        elif direction == "backward":
            self.pos[0] -= self.direction[0]*self.speed
            self.pos[1] -= self.direction[1]*self.speed
        
        print(self.pos)
    
    def draw(self, surface):
        # TEMP: constant to make sure tank points right way
        tank_correct_orient = -90
        rotated_image = pg.transform.rotate(self.image, -self.degrees+tank_correct_orient)
        rect = rotated_image.get_rect(center=self.pos)
        surface.blit(rotated_image, rect.topleft)

    def rotate(self, deg: int):
        self.degrees += deg
        rads = np.radians(self.degrees)
        self.direction = np.cos(rads), np.sin(rads)
        print(f"Rotation: {self.degrees}°, Direction: {self.direction}")
        
    def collision(self):
        # TODO
        pass
    
    def shoot(self):
        
        projectile = Projectile(self.pos[:], self.direction, speed=1.3)
        projectiles.append(projectile)
    
    
class Projectile:
    
    def __init__(self, startpos: tuple, direction: tuple, speed: int):
        self.pos = startpos
        self.direction = direction
        self.degrees = 0
        self.speed = speed
        #self.image = image
        self.lifespan = 500
        self.alive = True
        
    def update(self):
        self.pos[0] += self.direction[0]*self.speed
        self.pos[1] += self.direction[1]*self.speed
        
        self.lifespan -= 1
        
        if self.lifespan <= 0:
            self.alive = False
        
    def draw(self, surface):
        pg.draw.circle(surface, "red", (int(self.pos[0]), int(self.pos[1])), 2)
        
    def collision(self):
        pass


class Obstacle:
    
    def __init__(self, corners_list):
        self.corners = corners_list
        
    def draw(self, surface):    
        pg.draw.polygon(surface, "black", self.corners) 

if __name__ == "__main__":
    main()