import pygame as pg

class Track:
    def __init__(self, pos, angle, image, lifetime=50):
        self.pos = pos
        self.angle = angle
        self.original_image = image.convert_alpha()  # Ensure image has alpha channel
        self.lifetime = lifetime
        self.age = 0
        
        # Pre-rotate once on creation
        self.image = pg.transform.rotate(image, -angle).convert_alpha()
        self.rect = self.image.get_rect(center=pos)
        
    def update(self):
        self.age += 1
        return self.age < self.lifetime
        
    def draw(self, screen):
        alpha = max(0, 255 - int((self.age / self.lifetime) * 255))
        img = self.image.copy()
        img.set_alpha(alpha)  # Much faster
        screen.blit(img, self.rect)