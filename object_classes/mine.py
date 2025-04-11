import pygame as pg
import utils.deflect as df


class Mine:
    def __init__(self, spawn_point: tuple, explode_radius: int, owner_id: int):
        self.pos = tuple(spawn_point)
        self.explode_radius = explode_radius
        self.owner_id = owner_id
        self.is_exploded = False
        self.color = "yellow"
        self.unit_list = []

        self.countdown_start = False
        self.countdown_timer = 2 * 60     # 2 seconds
        self.life_timer = 10 * 60         # 10 seconds

        self.color_timer = 0
        self.min_flash_speed = 4

    def get_unit_list(self, unit_list: list):
        self.unit_list = unit_list

    def draw(self, surface):
        pg.draw.circle(surface, self.color, self.pos, 10)

        # Start countdown if life timer expires
        if not self.countdown_start:
            self.life_timer -= 1
            if self.life_timer <= 0:
                self.countdown_start = True

        # Handle flashing and explosion
        if self.countdown_start and not self.is_exploded:
            self.countdown_timer -= 1

            speed = max(self.min_flash_speed, self.countdown_timer // 20)
            self.color_timer -= 1

            if self.color_timer <= 0:
                self.color = "red" if self.color == "yellow" else "yellow"
                self.color_timer = speed

            if self.countdown_timer <= 0:
                self.explode()

    def check_for_tank(self, unit, check_for_owner=True):
        if check_for_owner and unit.id == self.owner_id:
            return False

        if self._is_in_radius(unit.pos):
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
