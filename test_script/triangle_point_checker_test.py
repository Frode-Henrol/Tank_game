




# a b c
triangle = [(0,0), (2,5), (2,0)]
point = (5, 3)
Px, Py = point
Ax, Ay = triangle[0]
Bx, By = triangle[1]
Cx, Cy = triangle[2]


import itertools

def check_triangle(triangle, point):
    # Get all permutations of the triangle vertices
    permutations = itertools.permutations(triangle)
    
    # We need to look at potentiel all permutations of the triangle, since some choices of A B C corners can led to division by zero error
    # Even though its a perfect valid triangle:
    for perm in permutations:
        Ax, Ay = perm[0]
        Bx, By = perm[1]
        Cx, Cy = perm[2]
        Px, Py = point

        # Try using the formula to check if point is inside triangle. Source: https://www.youtube.com/watch?v=HYAgJN3x4GA&ab_channel=SebastianLague
        try:
            w1 = (Ax * (Cy - Ay) + (Py - Ay) * (Cx - Ax) - Px * (Cy - Ay)) / ((By - Ay) * (Cx - Ax) - (Bx - Ax) * (Cy - Ay))
            w2 = (Py - Ay - w1 * (By - Ay)) / (Cy - Ay)

            if w1 >= 0 and w2 >= 0 and (w1 + w2) <= 1:
                print(True)
                return True
            else:
                print(False)
                return False

        except ZeroDivisionError:
            print("Division with 0, trying next permutation...")
            continue  # Try the next permutation

    # If no valid permutation is found, return False
    print(False)
    return False


check_triangle(triangle, point)

import pygame

# Initialize Pygame
pygame.init()

# Screen setup
screen = pygame.display.set_mode((600, 600))
pygame.display.set_caption("Triangle and Point Plot")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

screen.fill((255, 255, 255))  # Fill screen with white
# Triangle rendering
pygame.draw.polygon(screen, BLACK, [(Ax*100, Ay*100), (Bx*100, By*100), (Cx*100, Cy*100)], 2)

# Point rendering
pygame.draw.circle(screen, RED, (Px*100, Py*100), 5)

# Update the display
pygame.display.flip()

# Wait for the user to close the window
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

# Quit Pygame
pygame.quit()