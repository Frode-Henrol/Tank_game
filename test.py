import pygame

pygame.init()

# Create a window
screen = pygame.display.set_mode((500, 500))
pygame.display.set_caption("Mouse Click Positions")

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Detect mouse button down (click start)
        if event.type == pygame.MOUSEBUTTONDOWN:
            print(f"Mouse Down at: {event.pos}")

        # Detect mouse button up (click release)
        if event.type == pygame.MOUSEBUTTONUP:
            print(f"Mouse Up at: {event.pos}")

    pygame.display.update()

pygame.quit()
