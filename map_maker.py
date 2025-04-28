import pygame as pg
import sys
import utils.helper_functions as helper_functions
from object_classes.button import Button 
from object_classes.textfield import Textfield
import numpy as np
import os
import pathfinding

def main():
    
    mapsize = (800, 450)

    # Snap map size to the grid
    
    
    drawer = PolygonDrawer(1920, 1080, mapsize[0], mapsize[1])  # Adjust to your screen resolution
    drawer.run()


class PolygonDrawer:
    def __init__(self, WINDOW_W, WINDOW_H, map_width, map_height):
        
        pg.init()
        self.clock = pg.time.Clock()
        pg.display.set_caption("Polygon Drawer")
        self.fps = 30

        # Window setup
        #self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1320, 580
        self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = WINDOW_W, WINDOW_H
        self.SCALE = 30
        self.screen = pg.display.set_mode(self.WINDOW_DIM)
        self.WINDOW_DIM_SCALED = self.WINDOW_W_SCALED, self.WINDOW_H_SCALED = int(self.WINDOW_W / (self.SCALE * 1.5)), int(self.WINDOW_H / self.SCALE)

        self.points = []  # List to store the points of the polygon
        self.is_closed = False  # To check if the polygon is closed
        self.polygons: list[Polygon] = []   # List to store the polygons on the map
        self.map_name = ""
        self.map_name_only_display = ""
        
        self.map_folder_path = "map_files"  # skal rettes - skal måske kunne være custom?
        
        self.units = [] # List to store the units on the map
        
        self.map_width = map_width
        self.map_height = map_height
        
        self.map_borders = self.draw_map_border()
        
        # Store mouse postions
        self.mouse_pos1 = (0,0)
        self.mouse_pos2 = (0,0)
        self.snapped_pos = (0,0)
        
        # Starting state:
        self.state = States.MENU 
        
        # Starting mode in the editor
        self.editor_mode = EditorMode.POLYGON
        
        # Unit mode:
        self.selected_tank = None  # Keep track of the currently selected tank button
        self.tank_mappings = {0 : "player_tank", 1 : "brown_tank", 2 : "ash_tank", 3 : "marine_tank", 4 : "yellow_tank", 5 : "pink_tank", 6 : "green_tank", 7 : "violet_tank", 8 : "white_tank", 9 : "black_tank"}
        
        # Polygon mode:
        self.selected_polygon = 0   # Index: 0 = standard, 1 = destructible, 2 = pit
        self.polygon_colors = {0: "blue", 1: "red", 2: "grey"}

        # Path finding:
        self.node_spacing = 50
        self.show_pathfinding_nodes = False
        
        # Assets to load last
        self.load_gui()
        self.load_assets()
    
    
    def load_unit_images(self, name: str):
        
        path_tank = os.path.join(os.getcwd(),r"units\images", f"{name}.png")
        turret_name = name.split("_")[0]
        path_tank_turret = os.path.join(os.getcwd(),r"units\images", f"{turret_name}_turret.png")
        
        tank_img = pg.image.load(path_tank).convert_alpha()
        tank_img = pg.transform.scale(tank_img, self.WINDOW_DIM_SCALED)
        
        tank_turret_img = pg.image.load(path_tank_turret).convert_alpha()
        tank_turret_img = pg.transform.scale(tank_turret_img, (self.WINDOW_DIM_SCALED[0]*0.5, self.WINDOW_DIM_SCALED[1]*2))
        
        return [tank_img, tank_turret_img]
        

    def load_assets(self):
        self.tank_images = [self.load_unit_images(self.tank_mappings[i]) for i  in range(len(self.tank_mappings))]
        
    
    def load_gui(self):
        x_mid = self.WINDOW_W // 2
        y_mid = self.WINDOW_H // 2
        
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
            Button(left-150, 50, 600, 60, "---", hover_enabled=False, click_color_enabled=False),
            Button(left, 150, 300, 60, "Polygon placement", action = self.polygon_button, color_normal = standard_green_color),
            Button(left, 250, 300, 60, "Unit placement", action = self.unit_button, semi_disabled=True, color_normal = standard_green_color),
            Button(left, 350, 300, 60, "Editor", States.EDITOR),
            Textfield(left+350, 650, 300, 60, "-type map name-"),
            Textfield(left+350, 750, 300, 60, "-type map name-"),
            Button(left, 650, 300, 60, "Save map", action=lambda: self.save()),
            Button(left, 750, 300, 60, "Load map", action=lambda: self.load()),
            Button(left, 450, 300, 60, "Pathfinding", States.PATHFINDING),
            Button(left, 850, 300, 60, "Exit to main menu", States.MENU),
            Textfield(left-350, 250, 300, 60, "-map height-"),
            Textfield(left-350, 350, 300, 60, "-map width-")
        ]
        
        self.buttons_settings = [
            Button(left, 150, 300, 60, "1"),
            Button(left, 250, 300, 60, "2"),
            Button(left, 350, 300, 60, "2"),
            Textfield(left, 450, 300, 60, "Write name test"),
            Button(left, 550, 300, 60, "Back", States.EDITOR),
        ]
        
        self.button_pathfinding = [
            Button(left, 150, 300, 60, "Re-calculate nodes", action=self.update_pathfinding_nodes),
            Button(left, 250, 300, 60, "Show path nodes", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action = self.toggle_and_update),
            Button(left, 350, 300, 60, f"Node spacing: {self.node_spacing}", action=self.change_node_spacing, hover_enabled=False),
            Button(left, 450, 300, 60, "Back", States.EDITOR_MENU),
        ]
        
        # skal rettes: all buttons should be in a dictionary, to prevent this under:
        # A temp way to access the map save textfield/buttons for now
        self.textfield_map_save = self.buttons_editor_menu[4]
        self.textfield_map_load = self.buttons_editor_menu[5]
        
        self.textfield_map_height = self.buttons_editor_menu[10]
        self.textfield_map_width = self.buttons_editor_menu[11]
        
        self.map_name_only_display = self.buttons_editor_menu[0]
        
        self.node_spacing_button =  self.button_pathfinding[2]
        
        
        offset = 400
        offset_x = 600
        width = 120
        self.buttons_units = [
            Button(left+offset, 150, width, 60, "Player", action=lambda: self.unit_button_select(0), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset, 250, width, 60, "Brown", action=lambda: self.unit_button_select(1), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset, 350, width, 60, "Ash", action=lambda: self.unit_button_select(2), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset, 450, width, 60, "Marine", action=lambda: self.unit_button_select(3), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset, 550, width, 60, "Yellow", action=lambda: self.unit_button_select(4), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 150, width, 60, "Pink", action=lambda: self.unit_button_select(5), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 250, width, 60, "Green", action=lambda: self.unit_button_select(6), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 350, width, 60, "Violet", action=lambda: self.unit_button_select(7), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 450, width, 60, "White", action=lambda: self.unit_button_select(8), color_normal=standard_green_color, semi_disabled=True),
            Button(left+offset_x, 550, width, 60, "Black", action=lambda: self.unit_button_select(9), color_normal=standard_green_color, semi_disabled=True)
        ]
        
        self.buttons_polygons = [
              Button(left+offset, 150, width*1.8, 60, "Standard", action=lambda: self.polygon_button_select(0), color_normal=standard_green_color, semi_disabled=False),
              Button(left+offset, 250, width*1.8, 60, "Destructible", action=lambda: self.polygon_button_select(1), color_normal=standard_green_color, semi_disabled=True),
              Button(left+offset, 350, width*1.8, 60, "Pit", action=lambda: self.polygon_button_select(2), color_normal=standard_green_color, semi_disabled=True),
        ]
                
    # ===============================================================
    # functions for the buttons - this is a temp solution:
    def polygon_button(self):
        self.buttons_editor_menu[2].set_semi_disabled(True)     # Semi disable unit button
        self.editor_mode = EditorMode.POLYGON
        print("Polygon placement button clicked, editor mode set to POLYGON.")
        
    def unit_button(self):
        self.buttons_editor_menu[1].set_semi_disabled(True)     # Semi disable polygon button
        self.editor_mode = EditorMode.UNIT
        print("Unit placement button clicked, editor mode set to UNIT.")
        
    def unit_button_select(self, tank_index):
        # Set the pressed tank button to green
        for i, button in enumerate(self.buttons_units):
            if i == tank_index:
                self.selected_tank = tank_index  # Track the selected tank
                print(f"Selected tank {i+1} with 0-index: {i}")
            else:
                button.set_semi_disabled(True)  # Semi-disable other buttons
                
    def polygon_button_select(self, type_index):
        # Set the pressed button to green
        for i, button in enumerate(self.buttons_polygons):
            if i == type_index:
                self.selected_polygon = type_index  # Track the selected wall type
                print(f"Selected polygon type: {i}")
            else:
                button.set_semi_disabled(True)  # Semi-disable other buttons
        
    def change_node_spacing(self):
        # TEMP solution for choosing nodespacing. This should be a slider or textfield in the future?
        # skal rettes
        if self.node_spacing < 100:
            self.node_spacing +=25
        else:
            self.node_spacing = 25
            
        self.node_spacing_button.change_button_text(f"Node spacing: {self.node_spacing}")
        
        # Update the pathfinding nodes
        self.update_pathfinding_nodes()
    
    def toggle_and_update(self):
        helper_functions.toggle_bool(self, "show_pathfinding_nodes")
        self.update_pathfinding_nodes()
    
    def update_pathfinding_nodes(self):
        """ Updates the path finding nodes"""
        
        if self.show_pathfinding_nodes:
            polygon_list = [x.get_polygon_points() for x in self.polygons]
            
            _, self.valid_nodes = pathfinding.find_valid_nodes(self.map_borders, self.node_spacing, polygon_list)  
    
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
        """Main loop running the map maker"""
        
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
            elif self.state == States.PATHFINDING:
                self.pathfinding_settings(event_list)
                
            self.handle_global_events(event_list)
            self.clock.tick(self.fps)  # Limit to 30 FPS
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
            
        if self.editor_mode == EditorMode.POLYGON:
            self.handle_buttons(self.buttons_polygons, event_list, self.screen)
        
        for event in event_list:    # Skal rettes - Dette er gentaget kode pt. 
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.state = States.EDITOR
        
        # ============== Handle height and width textfield ================    
        # Get testfield 
        height_textfield = self.textfield_map_height.get_string()
        width_textfield = self.textfield_map_width.get_string()
        
        # Check if digits is written in the width and heigh text fields
        if height_textfield.isdigit() and width_textfield.isdigit():
            new_map_height = int(height_textfield)
            new_map_width = int(width_textfield)

            # Check if the height and width has changed to prevent calling draw_map_border each iteration
            if new_map_height != self.map_height or new_map_width != self.map_width:
                self.map_height = new_map_height
                self.map_width = new_map_width
                self.map_borders = self.draw_map_border()        
                    
    def pathfinding_settings(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.button_pathfinding, event_list, self.screen)    
            
    def settings(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.buttons_settings, event_list, self.screen)   
        
    def exit(self):
        self.save()
        pg.quit()
        sys.exit()
        
    def handle_global_events(self, event_list):
        """Handle events for all states"""
        for event in event_list:
            if event.type == pg.QUIT:
                self.exit()
            
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_q:  # If 'Q' key is pressed
                    self.exit()

# ========================================= EVENTS for each specific mode in the editor =========================================================

    def handle_editor_events_polygon_mode(self, event_list):
        for event in event_list:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_r: # Remove last polygon when pressing r
                    if self.polygons:
                        self.polygons.pop(-1)
                    # Update nodes if active
                    self.update_pathfinding_nodes()
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
                        self.polygons.append(Polygon(self.points, self.selected_polygon))
                        print("Polygone done")
                        self.points = []
                        
                        # Update nodes if active
                        self.update_pathfinding_nodes()
                    
                    else:
                        self.points.append(snapped_pos)  # Add snapped point to the list

    def handle_editor_events_units_mode(self, event_list):
        for event in event_list:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_r: # Remove last unit when pressing r
                    if self.units:
                        self.units.pop(-1)
                if event.key == pg.K_ESCAPE:
                    self.state = States.EDITOR_MENU
               
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.mouse_pos1 = pg.mouse.get_pos()

                    # Snap the mouse position to a grid of 50px spacing
                    self.snapped_pos = (snap_to_grid(self.mouse_pos1[0]), snap_to_grid(self.mouse_pos1[1]))
                    
                    print(self.snapped_pos)

            if event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:  # Left click
                    self.mouse_pos2 = pg.mouse.get_pos()
                    
                    # Find direction:
                    snapped_pos1 = self.snapped_pos # Reuse from when button was pressed down
                    snapped_pos2 = (snap_to_grid(self.mouse_pos2[0]), snap_to_grid(self.mouse_pos2[1]))
                    x1, y1 = snapped_pos1
                    x2, y2 = snapped_pos2
                    dx, dy = x1-x2, y1-y2
                    
                    # Use arctan2 to compute the correct angle
                    angle_rad = np.arctan2(dx, dy)
                    angle_deg = np.degrees(angle_rad)
                    self.rotate_offset = 90
                    angle_deg = (self.rotate_offset + angle_deg) % 360

                    if self.selected_tank is None:
                        print(f"Error: No unit selected.")
                        return
                    
                    for unit in self.units:
                        if self.snapped_pos == unit[0]:
                            print(f"Error: Can not place unit on top of other unit.")
                            return
                    
                    # Quick fix to prevent tank showing at (0,0) do to the self.snapped_pos being a class value initialized as (0,0) (Skal rettes)
                    if self.snapped_pos == (0, 0):  
                        return    
                    
                    # For now teams are player vs other
                    if self.selected_tank > 0:
                        team = 2
                    else:
                        team = 1
                    # Unit position, angle, type team saved is saved
                    self.units.append((self.snapped_pos, int(angle_deg), self.selected_tank, team))
                    print(f"Added unit at {self.snapped_pos} with angle {angle_deg} to the units list.")
                
# ===============================================================================================================================================

    def save(self):
        
        # Get map name from textfield
        self.map_name = f"{self.textfield_map_save.get_string()}.txt"
        
        # If textfield empty overwrite name to a standard
        if self.textfield_map_save.is_field_empty():
            print("No name is given")
            self.map_name = "map_test1.txt" # Use standard name if none given
        
        map_path = os.path.join(self.map_folder_path, self.map_name)
        
        with open(map_path, "w") as f:
            
            # Map name:
            f.write("Mapname:\n")
            f.write(f"{self.map_name}\n")
            # Write the map borders
            f.write("Polygons:\n")
            f.write(f"({self.map_borders},0)\n")    # The zero is to mark the border as standard polygon
            
            for polygon in self.polygons:

                # Convert tuples to list for json: (only to print console for test)
                no_tuple = [[x[0],x[1]] for x in polygon.get_polygon_points()]
                print(no_tuple)
                
                f.write(f"({polygon.get_polygon_points()},{polygon.polygon_type})\n")
            
            f.write("Units:\n")
            # If no units are added, there will automaticly be added a tank at a valid position
            if not self.units:
                self.show_pathfinding_nodes = True
                self.update_pathfinding_nodes()
                print("No units added. Adding player tank at valid node")
                self.units.append((self.valid_nodes[0], int(90), 0, 0))
            
            for unit in self.units:
                f.write(f"{unit}\n")
            
            f.write(f"Nodespacing: {self.node_spacing}")
            
        self.map_name_only_display.change_button_text(self.map_name)
        
    def load(self):
        
        # Clear all data before load
        self.polygons = []
        self.units = []
        
        # If the load textfield is used, get the string inside
        if self.textfield_map_load.is_field_empty():
            print("No name is given")
            return
        self.map_name = f"{self.textfield_map_load.get_string()}.txt"
        
        map_path = os.path.join(self.map_folder_path, self.map_name)
        
        # Load the objects and units into map editor
        polygons, polygons_with_type, units, self.node_spacing = helper_functions.load_map_data(map_path)
        for poly in polygons_with_type:
            print(poly)
        
        # Make sure to use first polygon as map borders and remove from the polygon list (reason is border wont be filed with solid color)
        self.map_borders = polygons[0]
        polygons.pop(0)
        polygons_with_type.pop(0)

        # Polygons need a class instance:
        for polygon_points, polygon_type in polygons_with_type:
            print(f"Polygon points: {polygon_points}")
            self.polygons.append(Polygon(polygon_points, polygon_type))
        
        print(f"Loaded {len(polygons)} obstacles.")
        print(f"Loaded {len(units)} units.")
        
        # Units at the moment is just a simple tuple, so no class instance needed
        self.units = units
        
        self.map_name_only_display.change_button_text(self.map_name)

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
            pg.draw.polygon(self.screen, self.polygon_colors[polygon.polygon_type], polygon.get_polygon_points())  # Fill with blue
        
        for corner_pair in helper_functions.coord_to_coordlist(self.map_borders):
            pg.draw.line(self.screen, "red", corner_pair[0], corner_pair[1], 3)

        # Draw the units images in unit mode
        for unit in self.units:
            unit_pos, unit_rotation, unit_type, _ = unit
           
            tank_body_image, tank_turret_image = self.tank_images[unit_type]
            
            
            rotated_unit_image = pg.transform.rotate(tank_body_image, unit_rotation - self.rotate_offset)
            rect = rotated_unit_image.get_rect(center=unit_pos)
            self.screen.blit(rotated_unit_image, rect.topleft)
            
            rotated_unit_image = pg.transform.rotate(tank_turret_image, unit_rotation - self.rotate_offset)
            rect = rotated_unit_image.get_rect(center=unit_pos)
            self.screen.blit(rotated_unit_image, rect.topleft)
            
        # Draw pathfinding nodes if turned on:
        if self.show_pathfinding_nodes:
            for node in self.valid_nodes:
                pg.draw.circle(self.screen, "purple", node, 5)
        
    def draw_grid(self):
        """Draw a faint grid on the screen."""
        grid_color = (200, 200, 200)  # Light gray for faint grid lines
        grid_opacity = 50  # Opacity (from 0 to 255)
        grid_color_with_opacity = grid_color + (grid_opacity,)

        # Draw vertical grid lines
        for x in range(0, self.WINDOW_W, 50):
            pg.draw.line(self.screen, grid_color_with_opacity, (x, 0), (x, self.WINDOW_H))

        # Draw horizontal grid lines
        for y in range(0, self.WINDOW_H, 50):
            pg.draw.line(self.screen, grid_color_with_opacity, (0, y), (self.WINDOW_W, y))

    def draw_map_border(self):
        # Find mid point
        mid_x = self.WINDOW_W // 2
        mid_y = self.WINDOW_H // 2

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
    
    def __init__(self, points, polygon_type):
        self.points = points
        self.polygon_type = polygon_type

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
    PATHFINDING = "pathfinding"

class EditorMode:
    POLYGON = "polygon"
    UNIT = "unit"
    
    


# Run the program with a specified window size
if __name__ == "__main__":
    main()
