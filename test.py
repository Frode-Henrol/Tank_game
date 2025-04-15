import pygame
import sys
import os

TEXTURE_PATH = os.path.join(os.getcwd(), "map_files", "backgrounds","dessert2.png")


import pygame

pygame.init()
screen = pygame.display.set_mode((1200, 900))

# Polygon points
polygon_points = [(400, 650), (850, 650), (850, 800), (800, 800), (800, 700), (400, 700)]

# Load texture and prepare it
texture = pygame.image.load(TEXTURE_PATH).convert()
texture = pygame.transform.scale(texture, (500, 150))  # scale to approximate size

# Create a surface with per-pixel alpha to draw polygon
polygon_surface = pygame.Surface((1200, 900), pygame.SRCALPHA)

# Fill polygon shape with white
pygame.draw.polygon(polygon_surface, (255, 255, 255, 255), polygon_points)

# Use the polygon_surface as a mask
mask = pygame.mask.from_surface(polygon_surface)
mask_surface = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))

# Prepare texture surface to match size
texture_surface = pygame.Surface((1200, 900), pygame.SRCALPHA)
for x in range(0, 1200, texture.get_width()):
    for y in range(0, 900, texture.get_height()):
        texture_surface.blit(texture, (x, y))



# Apply mask to texture
texture_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)






# Main loop
running = True
while running:
    screen.fill((30, 30, 30))

    screen.blit(texture_surface, (0, 0))  # draw textured polygon

    pygame.draw.polygon(screen, (255, 255, 255), polygon_points, 2)  # optional outline

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()

pygame.quit()


"""def wrap_texture_on_polygon(self, polygon_points, texture, texture_path):
    # Polygon points

    # Load texture and prepare it
    texture = pg.image.load(texture_path).convert()
    texture = pg.transform.scale(texture, (500, 150))  # scale to approximate size

    # Create a surface with per-pixel alpha to draw polygon
    polygon_surface = pg.Surface((self.WINDOW_DIM_SCALED), pg.SRCALPHA)

    # Fill polygon shape with white
    pg.draw.polygon(polygon_surface, (255, 255, 255, 255), polygon_points)

    # Use the polygon_surface as a mask
    mask = pg.mask.from_surface(polygon_surface)
    mask_surface = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))

    # Prepare texture surface to match size
    texture_surface = pg.Surface((self.WINDOW_DIM_SCALED), pg.SRCALPHA)
    for x in range(0, self.WINDOW_DIM_SCALED[0], texture.get_width()):
        for y in range(0, self.WINDOW_DIM_SCALED[1], texture.get_height()):
            texture_surface.blit(texture, (x, y))

    # Apply mask to texture
    texture_surface.blit(mask_surface, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
    return texture_surface"""