import pygame as pg


class Animation:
    def __init__(self, images: list, frame_delay: int):
        self.images = images
        self.frame_delay = frame_delay
        self.image_index = 0
        self.frame_counter = 0
        self.finished = False
        self.has_played = False
        self.angle = 0
        self.pos = (0, 0)

    def start(self, pos, angle):
        self.pos = pos
        self.angle = angle
        self.image_index = 0
        self.frame_counter = 0
        self.finished = False
        self.has_played = True

    def play(self, screen):
        if self.finished or self.image_index >= len(self.images):
            self.finished = True
            return

        image = self.images[self.image_index]
        rotated = pg.transform.rotate(image, -self.angle)
        rect = rotated.get_rect(center=self.pos)
        screen.blit(rotated, rect)

        self.frame_counter += 1
        if self.frame_counter >= self.frame_delay:
            self.frame_counter = 0
            self.image_index += 1

        
        
    