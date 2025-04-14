import pygame as pg

class Track:
    def __init__(self, pos, angle, image, lifetime=250):
        self.pos = pos
        self.angle = angle
        self.original_image = image.convert_alpha()  # Ensure image has alpha channel
        self.lifetime = lifetime
        self.age = 0
        
    def update(self):
        self.age += 1
        return self.age < self.lifetime
        
    def draw(self, screen):
        # Calculate fade alpha (255 = fully opaque, 0 = fully transparent)
        alpha = max(0, 255 - int((self.age / self.lifetime) * 255))
        
        # Create a copy of the image to modify
        faded_image = self.original_image.copy()
        
        # Apply alpha to all pixels
        faded_image.fill((255, 255, 255, alpha), special_flags=pg.BLEND_RGBA_MULT)
        
        # Rotate and draw
        rotated = pg.transform.rotate(faded_image, -self.angle)
        rect = rotated.get_rect(center=self.pos)
        screen.blit(rotated, rect)