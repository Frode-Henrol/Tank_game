import pygame as pg
import sys

class PolygonDrawer:
    def __init__(self, window_width, window_height):
        self.window_width = window_width
        self.window_height = window_height
        self.points = []  # List to store the points of the polygon
        self.is_closed = False  # To check if the polygon is closed
        
        self.polygons: list[Polygon] = []
        
        pg.init()
        self.screen = pg.display.set_mode((window_width, window_height))
        pg.display.set_caption("Polygon Drawer")
        self.clock = pg.time.Clock()

    def run(self):
        """Main loop for drawing the polygon."""
        while True:
            self.handle_events()
            self.draw()
            self.clock.tick(30)  # Limit to 30 FPS

    def handle_events(self):
        """Handle all events."""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                exit()
            
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_q:  # If 'Q' key is pressed
                    pg.quit()
                    exit()
                if event.key == pg.K_r: # Remove last polygon when pressing r
                    self.polygons.pop(-1)
                
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = pg.mouse.get_pos()

                    # Snap the mouse position to a grid of 50px spacing
                    snapped_pos = (self.snap_to_grid(mouse_pos[0]), self.snap_to_grid(mouse_pos[1]))

                    # If the first point is clicked again, close the polygon
                    if len(self.points) > 0 and self.is_point_near(snapped_pos, self.points[0]):
                        self.is_closed = True  # Close the polygon
                        self.polygons.append(Polygon(self.points))
                        print("Polygone done")
                        self.points = []
                    
                    else:
                        self.points.append(snapped_pos)  # Add snapped point to the list

    def snap_to_grid(self, value):
        """Snap a value to the nearest multiple of 50."""
        return round(value / 50) * 50

    def is_point_near(self, point, compare_point, threshold=10):
        """Check if a point is near the first point (to close the polygon)."""
        x, y = point
        cx, cy = compare_point
        return abs(x - cx) < threshold and abs(y - cy) < threshold

    def draw(self):
        """Draw the polygon and points on the screen."""
        self.screen.fill((255, 255, 255))  # Fill screen with white
        
        # Draw the faint grid
        self.draw_grid()

        # Draw the polygon
        if len(self.points) > 1:
            pg.draw.lines(self.screen, (0, 0, 0), False, self.points, 3)  # Draw lines connecting points

        # Draw the points as small circles
        for point in self.points:
            pg.draw.circle(self.screen, (255, 0, 0), point, 5)

        # Draw the circle that follows the mouse but clips to the nearest point
        mouse_pos = pg.mouse.get_pos()
        snapped_pos = (self.snap_to_grid(mouse_pos[0]), self.snap_to_grid(mouse_pos[1]))
        pg.draw.circle(self.screen, (0, 255, 0), snapped_pos, 10)  # Circle follows the mouse but clipped

        # If the polygon is closed, fill it with a semi-transparent color
        for polygon in self.polygons:
            pg.draw.polygon(self.screen, (0, 0, 255, 100), polygon.get_polygon_points())  # Fill with blue

        pg.display.flip()  # Update the screen

    def draw_grid(self):
        """Draw a faint grid on the screen."""
        grid_color = (200, 200, 200)  # Light gray for faint grid lines
        grid_opacity = 50  # Opacity (from 0 to 255)
        grid_color_with_opacity = grid_color + (grid_opacity,)

        # Draw vertical grid lines
        for x in range(0, self.window_width, 50):
            pg.draw.line(self.screen, grid_color_with_opacity, (x, 0), (x, self.window_height))

        # Draw horizontal grid lines
        for y in range(0, self.window_height, 50):
            pg.draw.line(self.screen, grid_color_with_opacity, (0, y), (self.window_width, y))

class Polygon:
    
    def __init__(self, points):
        self.points = points

    def get_polygon_points(self):
        return self.points

# Run the program with a specified window size
if __name__ == "__main__":
    drawer = PolygonDrawer(800, 600)
    drawer.run()
