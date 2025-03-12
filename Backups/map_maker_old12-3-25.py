import pygame as pg
import sys
import utils.helper_functions as helper_functions
from object_classes.button import Button 
import numpy as np
import os

def main():
    
    mapsize = (900, 450)
    map_name = r"map_files\map_test1.txt"
    # Snap map size to the grid
    
    
    drawer = PolygonDrawer(1920, 1080, mapsize[0], mapsize[1], map_name)  # Adjust to your screen resolution
    drawer.run()



class PolygonDrawer:
    def __init__(self, window_width, window_height, map_width, map_height, map_name):
        
        
        
        
        self.window_width = window_width
        self.window_height = window_height
        self.points = []  # List to store the points of the polygon
        self.is_closed = False  # To check if the polygon is closed
        self.polygons: list[Polygon] = []
        self.map_name = map_name
        
        self.units = []     # Skal rettes - test af unit list
        
        self.map_width = map_width
        self.map_height = map_height
        
        self.map_borders = self.draw_map_border()
        
        # Store mouse postions
        self.mouse_pos1 = (0,0)
        self.mouse_pos2 = (0,0)
        self.snapped_pos = (0,0)
        
        
        pg.init()
        self.screen = pg.display.set_mode((window_width, window_height))
        pg.display.set_caption("Polygon Drawer")
        self.clock = pg.time.Clock()
        
        # Starting state:
        self.state = States.MENU 
        
        # Starting mode in the editor
        self.editor_mode = EditorMode.POLYGON
        
        # UNIT MODE:
        self.selected_tank = None  # Keep track of the currently selected tank button
        
        self.load_gui()
    
    def load_assets(self):
        """Load and scale game assets (e.g., images)."""
        try:
            path_tank = os.path.join(os.getcwd(),r"units\lvl1_tank", "tank2.png")

            self.tank_img = pg.image.load(path_tank).convert_alpha()
            self.tank_img = pg.transform.scale(self.tank_img, self.WINDOW_DIM_SCALED)
            
        except FileNotFoundError:
            print("Error: Image not found! Check your path.")
            sys.exit()
            
    
    def load_gui(self):
        x_mid = self.window_width // 2
        y_mid = self.window_height // 2
        
        # ==================== Button for states ====================
        # Last argument for button tells the button which state it should change to
        
        button_width = 300
        left = x_mid - button_width // 2    # The x value were button starts
        standard_green_color = (0, 100, 0)
        
        self.buttons_menu = [
            Button(left, 150, 300, 60, "Start editor", States.EDITOR_MENU),
            Button(left, 250, 300, 60, "Settings", States.SETTINGS),
            Button(left, 350, 300, 60, "Quit", States.EXIT)
        ]
                
        self.buttons_editor_menu = [
            Button(left, 150, 300, 60, "Polygon placement", action = self.polygon_button, color_normal = standard_green_color),
            Button(left, 250, 300, 60, "Unit placement", action = self.unit_button, semi_disabled=True, color_normal = standard_green_color),
            Button(left, 350, 300, 60, "Editor", States.EDITOR),
            Button(left, 550, 300, 60, "Save map to json"),
            Button(left, 650, 300, 60, "Exit to main menu", States.MENU),
            
        ]
        
        self.buttons_settings = [
            Button(left, 150, 300, 60, "1"),
            Button(left, 250, 300, 60, "2"),
            Button(left, 350, 300, 60, "2"),
            Button(left, 450, 300, 60, "2"),
            Button(left, 550, 300, 60, "Back", States.MENU),
        ]
        
        
        offset = 400
        offset_x = 600
        width = 120
        self.buttons_units = [
            Button(left+offset, 150, width, 60, "Tank 1", action=lambda: self.tank_button(0), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset, 250, width, 60, "Tank 2", action=lambda: self.tank_button(1), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset, 350, width, 60, "Tank 3", action=lambda: self.tank_button(2), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset, 450, width, 60, "Tank 4", action=lambda: self.tank_button(3), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset, 550, width, 60, "Tank 5", action=lambda: self.tank_button(4), color_normal=standard_green_color, semi_disabled=True),

            Button(left+offset_x, 150, width, 60, "Tank 6", action=lambda: self.tank_button(5), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 250, width, 60, "Tank 7", action=lambda: self.tank_button(6), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 350, width, 60, "Tank 8", action=lambda: self.tank_button(7), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 450, width, 60, "Tank 9", action=lambda: self.tank_button(8), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 550, width, 60, "Tank 10", action=lambda: self.tank_button(9), color_normal=standard_green_color, semi_disabled=True)
        ]
                
    # ===============================================================
    # functions for the buttons - this is a temp solution:
    def polygon_button(self):
        self.buttons_editor_menu[1].set_semi_disabled(True)     # Semi disable unit button
        self.editor_mode = EditorMode.POLYGON
        print("Polygon placement button clicked, editor mode set to POLYGON.")
        
    def unit_button(self):
        self.buttons_editor_menu[0].set_semi_disabled(True)     # Semi disable polygon button
        self.editor_mode = EditorMode.UNIT
        print("Unit placement button clicked, editor mode set to UNIT.")
        
    
    def tank_button(self, tank_index):
        # Set the pressed tank button to green
        for i, button in enumerate(self.buttons_units):
            if i == tank_index:
                self.selected_tank = tank_index  # Track the selected tank
                print(f"Selected tank {i+1} with 0-index: {i}")
            else:
                button.set_semi_disabled(True)  # Semi-disable other buttons
        
    # ===============================================================
        
        
    def handle_buttons(self, button_list, event_list, screen):
        """Handles button events and drawing of buttons"""
        for event in event_list:
            for button in button_list:
                # Each button checks for click
                new_state = button.handle_event(event)
                if new_state:
                    self.state = new_state
        
        for button in button_list:
            button.draw(screen)
        
    def run(self):
        """Main loop for drawing the polygon."""
        
        # Init the map border lines:
        while True:
            event_list = pg.event.get()
            
            if self.state == States.MENU:
                self.menu(event_list)
            elif self.state == States.EDITOR_MENU:
                self.editor_menu(event_list)                
            elif self.state == States.EDITOR:
                self.editor(event_list)
            elif self.state == States.EXIT:
                self.exit()
            elif self.state == States.SETTINGS:
                self.settings(event_list)
                
            self.handle_global_events(event_list)
            self.clock.tick(30)  # Limit to 30 FPS
            pg.display.flip()  # Update the screen            
    
    def menu(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.buttons_menu, event_list, self.screen)
        
    def editor(self, event_list):
        
        if self.editor_mode == EditorMode.POLYGON:
            self.handle_editor_events_polygon_mode(event_list)
        
        if self.editor_mode == EditorMode.UNIT:
            self.handle_editor_events_units_mode(event_list)
            
        self.draw()
        
    def editor_menu(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.buttons_editor_menu, event_list, self.screen) 
        
        # If unit mode, then show the buttons for each unit
        if self.editor_mode == EditorMode.UNIT:
            self.handle_buttons(self.buttons_units, event_list, self.screen) 
        
        for event in event_list:    # Skal rettes - Dette er gentaget kode pt. 
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.state = States.EDITOR
    
    def settings(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.buttons_settings, event_list, self.screen)   
        
    def exit(self):
        pg.quit()
        sys.exit()
        
    def handle_global_events(self, event_list):
        """Handle events for all states"""
        for event in event_list:
            if event.type == pg.QUIT:
                self.exit()
            
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_q:  # If 'Q' key is pressed
                    self.save()
                    self.exit()
    
# ========================================= EVENTS for each specific mode in the editor =========================================================

    def handle_editor_events_polygon_mode(self, event_list):
        for event in event_list:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_r: # Remove last polygon when pressing r
                    self.polygons.pop(-1)
                if event.key == pg.K_ESCAPE:
                    self.state = States.EDITOR_MENU
               
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = pg.mouse.get_pos()

                    # Snap the mouse position to a grid of 50px spacing
                    snapped_pos = (snap_to_grid(mouse_pos[0]), snap_to_grid(mouse_pos[1]))              # Skal rettes. Pt er snapped pos i unit state lavet til et class var self.snapped_pos - potentielt skulle polygon state også for consistensys

                    # If the first point is clicked again, close the polygon
                    if len(self.points) > 0 and self.is_point_near(snapped_pos, self.points[0]):
                        self.is_closed = True  # Close the polygon
                        self.polygons.append(Polygon(self.points))
                        print("Polygone done")
                        self.points = []
                    
                    else:
                        self.points.append(snapped_pos)  # Add snapped point to the list

    
    def handle_editor_events_units_mode(self, event_list):
        for event in event_list:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_r: # Remove last unit when pressing r
                    self.units.pop(-1)
                if event.key == pg.K_ESCAPE:
                    self.state = States.EDITOR_MENU
               
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.mouse_pos1 = pg.mouse.get_pos()

                    # Snap the mouse position to a grid of 50px spacing
                    self.snapped_pos = (snap_to_grid(self.mouse_pos1[0]), snap_to_grid(self.mouse_pos1[1]))
                    
                    print(self.snapped_pos)
                    if self.selected_tank is None:
                        print(f"Error: No unit selected.")
                        return
                    if self.snapped_pos in self.units:
                        print(f"Error: Can not place unit on top of other unit.")
                        return

                    
            if event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:  # Left click
                    self.mouse_pos2 = pg.mouse.get_pos()
                    
                    # Find direction:
                    snapped_pos1 = self.snapped_pos # Reuse from when button was pressed down
                    snapped_pos2 = (snap_to_grid(self.mouse_pos2[0]), snap_to_grid(self.mouse_pos2[1]))
                    x1, y1 = snapped_pos1
                    x2, y2 = snapped_pos2
                    dx, dy = x2-x1, y2-y1
                    
                    # Use arctan2 to compute the correct angle
                    angle_rad = np.arctan2(dy, dx)
                    angle_deg = np.degrees(angle_rad)

                    self.units.append((self.snapped_pos, angle_deg))
                    print(f"Added unit at {self.snapped_pos} with angle {angle_deg} to the units list.")
                

# ===============================================================================================================================================


    def save(self):
        with open(self.map_name, "w") as f:
                        
            # Map name:
            f.write(f"{self.map_name}\n")
            # Write the map borders
            f.write(f"{self.map_borders}\n")
            
            for polygon in self.polygons:

                # Convert tuples to list for json: (only to print console for test)
                no_tuple = [[x[0],x[1]] for x in polygon.get_polygon_points()]
                print(no_tuple)
                
                f.write(f"{polygon.get_polygon_points()}\n")
    

        
    

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
        snapped_pos = (snap_to_grid(mouse_pos[0]), snap_to_grid(mouse_pos[1]))
        pg.draw.circle(self.screen, (0, 255, 0), snapped_pos, 10)  # Circle follows the mouse but clipped

        # If the polygon is closed, fill it with a semi-transparent color
        for polygon in self.polygons:
            pg.draw.polygon(self.screen, (0, 0, 255, 100), polygon.get_polygon_points())  # Fill with blue
        
        for corner_pair in helper_functions.coord_to_coordlist(self.map_borders):
            pg.draw.line(self.screen, "red", corner_pair[0], corner_pair[1], 3)

        # Draw the units as circles in unit mode
        for unit in self.units:
            unit_pos = unit[0]
            pg.draw.circle(self.screen, (0, 0, 255), unit_pos, 15)  # Blue circles for units
    

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

    def draw_map_border(self):
        # Find mid point
        mid_x = self.window_width // 2
        mid_y = self.window_height // 2

        # Snap map width and height to grid
        snapped_map_width = snap_to_grid(self.map_width)
        snapped_map_height = snap_to_grid(self.map_height)
        
        print(f"Map middle: {snapped_map_width=} {snapped_map_height}")

        # Calculate the map border coordinates snapped to the grid
        corners =  [ 
            (snap_to_grid(mid_x - snapped_map_width // 2) , snap_to_grid(mid_y + snapped_map_height // 2)),
            (snap_to_grid(mid_x + snapped_map_width // 2) , snap_to_grid(mid_y + snapped_map_height // 2)), 
            (snap_to_grid(mid_x + snapped_map_width // 2) , snap_to_grid(mid_y - snapped_map_height // 2)),
            (snap_to_grid(mid_x - snapped_map_width // 2) , snap_to_grid(mid_y - snapped_map_height // 2))
        ]
        
        
        print(f"{corners=}")
        return corners

  
class Polygon:
    
    def __init__(self, points):
        self.points = points

    def get_polygon_points(self):
        return self.points

def snap_to_grid(value):
    """Snap a value to the nearest multiple of 50."""
    return round(value / 50) * 50


class States:
    EDITOR = "editor"
    EDITOR_MENU = "editor_menu"
    MENU = "menu"
    EXIT = "exit"
    SETTINGS = "settings"

class EditorMode:
    POLYGON = "polygon"
    UNIT = "unit"
    
    


# Run the program with a specified window size
if __name__ == "__main__":
    main()
