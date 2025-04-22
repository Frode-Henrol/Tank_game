import pygame as pg
import random

from object_classes.animation import Animation

class Mine:
    def __init__(self, image, spawn_point: tuple, explode_radius: int, owner_id: int, team: int):
        self.pos = tuple(spawn_point)
        self.explode_radius = explode_radius
        self.owner_id = owner_id
        self.team = team
        self.is_exploded = False
        self.color = "yellow"
        self.unit_list = []
        self.image = image
        self.countdown_timer = 2 * 60    # 2 seconds
        self.life_timer = 10 * 60         # 10 seconds
    
        self.countdown_start = False
        self.timer_set = False

        self.color_timer = 0
        self.min_flash_speed = 4
    
    def get_unit_list(self, unit_list: list):
        self.unit_list = unit_list

    def draw(self, surface):
        pg.draw.circle(surface, self.color, self.pos, 10)
        
        # TODO use mine image and rewrite the flashing logic to image
        # tank_rect = self.image.get_rect(center=self.pos)
        # surface.blit(self.image, tank_rect.topleft)

    def update(self, delta_time):
        self.delta_time = delta_time
        # Start countdown if life timer expires
        if not self.countdown_start:
            self.life_timer -= 60 * self.delta_time
            if self.life_timer <= 0:
                self.countdown_start = True

        # Handle flashing and explosion
        if self.countdown_start and not self.is_exploded:
            self.countdown_timer -= 60 * self.delta_time

            speed = max(self.min_flash_speed, self.countdown_timer // 20)
            self.color_timer -= 60 * self.delta_time

            if self.color_timer <= 0:
                self.color = "red" if self.color == "yellow" else "yellow"
                self.color_timer = speed

            if self.countdown_timer <= 0:
                self.explode()

    def check_for_tank(self, unit, check_for_owner=True):
        if check_for_owner and unit.team == self.team or unit.dead:
            return False
        
        if self._is_in_radius(unit.pos):
            
            if not self.countdown_start:
                self.countdown_timer *= 0.25   # Shorten coundown timer if mine is triggered by enemy tank
            
            self.countdown_start = True
            return True
        return False

    def explode(self):
        for unit in self.unit_list:
            if self._is_in_radius(unit.pos):
                unit.make_dead(True)

        self.is_exploded = True
        self.color = "red"
        


    def _is_in_radius(self, target_pos):
        x, y = target_pos
        cx, cy = self.pos
        return (x - cx)**2 + (y - cy)**2 < self.explode_radius**2
