import pygame as pg
import utils.deflect as df


class Mine:
    
    def __init__(self, spawn_point: tuple, explode_radius: int):
        self.spawn_point = spawn_point
        self.explode_radius = explode_radius
        self.is_exploded = False
    
    def draw(self, surface):
        pg.draw.circle(surface, "yellow", self.spawn_point, 10)
    
    def check_for_tank(self, tank_pos: tuple):
        
        x, y = tank_pos
        cx, cy = self.spawn_point
        
        if (x - cx)**2 + (y - cy)**2 < self.explode_radius**2:
            self.is_exploded = True
            # Need som logic that makes it explode after some time and kill tanks
            
            return True
        return False
    
    # Need logic that remove speciel polygons that can be destroyed.
    
        
    
    
    
    
    
    
    
    
        
    
    
    