

import pygame
pygame.init()

# Setup
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Sound Demo")
clock = pygame.time.Clock()

# Load sound
click_sound = pygame.mixer.Sound(r"sound_effects\cannon.wav")
click_sound.set_volume(0.1)  # Range: 0.0 to 1.0

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            click_sound.play()

    screen.fill((30, 30, 30))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
