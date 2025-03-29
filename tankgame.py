
import sys
import pygame as pg
import numpy as np
import os
import utils.helper_functions as helper_functions
import time
from object_classes.projectile import Projectile
from object_classes.tank import Tank
from object_classes.obstacle import Obstacle
from object_classes.button import Button 
import json
import pathfinding

class TankGame:
    def __init__(self):
        # Initialize Pygame
        pg.init()
        self.clock = pg.time.Clock()
        self.fps = 60

        # Window setup
        #self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1320, 580
        self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1980, 1200
        self.SCALE = 30
        self.screen = pg.display.set_mode(self.WINDOW_DIM)
        self.WINDOW_DIM_SCALED = self.WINDOW_W_SCALED, self.WINDOW_H_SCALED = int(self.WINDOW_W / (self.SCALE * 1.5)), int(self.WINDOW_H / self.SCALE)
        self.display = pg.Surface(self.WINDOW_DIM_SCALED)

        # Game objects
        self.units: list[Tank] = []
        self.units_player_controlled: list[Tank] = []
        
        self.projectiles: list[Projectile] = []
        self.obstacles: list[Obstacle] = []
        
        
        # Game states:
        self.state = States.MENU

        # Load assets
        self.load_assets()

        # Initialize game objects - SKAL Rettes denne function skal omskrives sådan den init baseret på den rigtige json fil med map data
        self.init_game_objects()

        # Load gui related features
        self.load_gui()
        
        # Settings menu:
        self.show_obstacle_corners = False
        self.draw_hitbox = True # Not implemented 
        self.godmode = False    # Not implemented 
        self.show_pathfinding_nodes = False
        self.show_pathfinding_paths = False

        # Pathfinding
        self.all_unit_waypoint_queues = []
        

    def load_gui(self):
        x_mid = self.WINDOW_DIM[0] // 2
        y_mid = self.WINDOW_DIM[1] // 2
        
        # ==================== Button for states ====================
        # Last argument for button tells the button which state it should change to
        
        button_width = 300
        left = x_mid - button_width // 2    # The x value were button starts
        
        self.menu_buttons = [
            Button(left, 150, 300, 60, "Level selection", States.LEVEL_SELECT),
            Button(left, 250, 300, 60, "Settings", States.SETTINGS),
            Button(left, 350, 300, 60, "Quick play", States.COUNTDOWN),
            Button(left, 450, 300, 60, "Quit", States.EXIT)
        ]
        
        self.setting_buttons = [
            Button(left, 150, 300, 60, "Show obstacle corners", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda: helper_functions.toggle_bool(self, "show_obstacle_corners")),
            Button(left, 250, 300, 60, "Draw hitbox", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "draw_hitbox")),
            Button(left, 350, 300, 60, "Godmode", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "godmode")),
            Button(left, 450, 300, 60, "Show pathfinding nodes", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_pathfinding_nodes")),
            Button(left, 550, 300, 60, "Show pathfinding paths", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_pathfinding_paths")),
            Button(left, 650, 300, 60, "Back", States.MENU)
        ]
        
        self.level_selection_buttons = [
            Button(left, 150, 300, 60, "Level 1", States.PLAYING, action=self.load_map(map_num=1)),
            Button(left, 250, 300, 60, "Level 2", States.PLAYING, action=self.load_map(map_num=2)),
            Button(left, 350, 300, 60, "Level 3", States.PLAYING, action=self.load_map(map_num=3)),
            Button(left, 450, 300, 60, "Level 4", States.PLAYING, action=self.load_map(map_num=4)),

            Button(left, 550, 300, 60, "Back", States.MENU)  
        ]
            
    def load_map(self, map_num):
        print(f"MAP {map_num} loadet")
        # not implemented
        
        
    
    def load_assets(self):
        """Load and scale game assets (e.g., images)."""
        try:
            path_tank = os.path.join(os.getcwd(),r"units\lvl1_tank", "tank2.png")
            path_tank_death = os.path.join(os.getcwd(), r"units\death_images", "tank_death2.png")

            self.tank_img = pg.image.load(path_tank).convert_alpha()
            self.tank_img = pg.transform.scale(self.tank_img, self.WINDOW_DIM_SCALED)

            self.tank_death_img = pg.image.load(path_tank_death).convert_alpha()
            self.tank_death_img = pg.transform.scale(self.tank_death_img, (self.WINDOW_DIM_SCALED[0]*2,self.WINDOW_DIM_SCALED[1]*2))
            
        except FileNotFoundError:
            print("Error: Image not found! Check your path.")
            sys.exit()

    def init_game_objects(self):
        """Initialize tanks and obstacles."""
        
        # ============== all this i temp! should be map based! ================================
        speed = 144 / self.fps        # 144 is just a const based on the speed i first tested game at
        firerate = 2
        speed_projectile = 2
        speed_projectile *= speed
        spawn_point  = (800, 500)
        spawn_degrees = 45
        bounch_limit = 1
        bomb_limit = 0
        
        #player_tank = Tank(spawn_point, speed, firerate, speed_projectile, spawn_degrees, bounch_limit, bomb_limit, self.tank_img, self.tank_death_img, use_turret=True)
        #self.units.append(player_tank)
        
        # SKAL RETTES - test tank for teste ai
        #player_tank = Tank((600,500), speed, firerate, speed_projectile, spawn_degrees, bounch_limit, bomb_limit, self.tank_img, self.tank_death_img, use_turret=True)
        #self.units.append(player_tank)

        # Map data i a tuple, where 1 entre is the polygon defining the map border the second is a list of all polygon cornerlists
        map_name = r"map_files\map_test1.txt"
        self.polygon_list, unit_list, self.node_spacing = helper_functions.load_map_data(map_name)
       
        # Skal RETTES: Store polygon corners for detection (this is currently not used, just a test) ctrl-f (Test MED DETECT)
        self.polygon_list_no_border = self.polygon_list.copy()
        self.border_polygon = self.polygon_list_no_border.pop(0)    # Removes the border polygon and store seperate
        
        # Get pathfinding data from map.
        self.grid_dict = pathfinding.get_mapgrid_dict(self.polygon_list.copy(), self.node_spacing)
        
        # Get valid nodes for path finding visuals
        _, self.valid_nodes = pathfinding.find_valid_nodes(self.border_polygon, self.node_spacing, self.polygon_list_no_border) 
        print(f"VALID NODES: {self.valid_nodes}")
        
        # ==================== Load map obstacles and units ====================
        for polygon_conrners in self.polygon_list:
            self.obstacles.extend([Obstacle(polygon_conrners)])
        
        # Open unit json to get unit info
        all_units_data_json_path = r"units\units.json"
        
        # Tank mappings dict (maps a number to the json name, since map_files use number to store tank type, Could be done with list also, since tank numbering is 0-index)
        tank_mappings = {0 : "tank1", 1 : "tank2"}
        
        with open(all_units_data_json_path, "r") as json_file:
                
            all_units_data_json = json.load(json_file)
            print(f"Loaded unit dict: {all_units_data_json}")
        
            # Unpack each unit map data
            for unit in unit_list:
                unit_pos, unit_angle, unit_type = unit
                
                # Get unit type in json format
                unit_type_json_format = tank_mappings[unit_type]
                
                # Fetch specific unit data 
                specific_unit_data = all_units_data_json[unit_type_json_format]
                
                temp_speed = 144 / self.fps 
                # TODO Tank image most be based on specific tank type! - Right know it is using the same. (the json already has a mapping for image name (could be removed, since type could be used to find correct picture))
                
                # Make sure that if the ai type is set to None if it is a player controlled tank
                if specific_unit_data["ai_personality"] == "player":
                    print(f"Tank {unit} is player controlled.")
                    ai_type = None
                else:
                    ai_type = specific_unit_data["ai_personality"]
                
                try:
                    unit_to_add = Tank(startpos            = unit_pos,
                                        speed              = temp_speed * specific_unit_data["tank_speed_modifier"], 
                                        firerate           = specific_unit_data["firerate"],
                                        speed_projectile   = temp_speed * specific_unit_data["projectile_speed_modifier"],
                                        spawn_degress      = unit_angle,
                                        bounch_limit       = specific_unit_data["bounch_limit"] + 1,
                                        bomb_limit         = specific_unit_data["bomb_limit"],
                                        image              = self.tank_img,
                                        death_image        = self.tank_death_img,
                                        use_turret         = True, 
                                        ai_type            = ai_type)
                    
                    if unit_to_add.get_ai() == None:
                        self.units_player_controlled.append(unit_to_add)
                        
                    self.units.append(unit_to_add)
                    
                except Exception as e:
                    print(f"Error: {e}")
            

    def run(self):
        """Main game loop."""
        while True:
            
            event_list = pg.event.get()
            
            if self.state == States.MENU:
                self.main_menu(event_list)
            elif self.state == States.SETTINGS:
                self.settings(event_list)
            elif self.state == States.LEVEL_SELECT:
                self.level_selection(event_list)
            elif self.state == States.PLAYING:
                self.playing(event_list)
            elif self.state == States.COUNTDOWN:
                self.count_down(event_list)
            elif self.state == States.EXIT:
                self.exit()
            
            self.handle_events(event_list)

    # ============================================ State methods ============================================
    # ============================================ ------------- ============================================
    def main_menu(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.menu_buttons, event_list, self.screen)
        pg.display.update()

    def exit(self):
        pg.quit()
        sys.exit()
        
    def settings(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.setting_buttons, event_list, self.screen)
        pg.display.update()
    
    def level_selection(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.level_selection_buttons, event_list, self.screen)
        pg.display.update()
    
    def count_down(self, eventlist):
        # Set countdown starting number (for example, 3 seconds)
        countdown_number = 1
        font = pg.font.Font(None, 200)  # Large font for the countdown number
        
        while countdown_number > 0:
            self.draw() # Drawing all objects
            
            # Setup text
            countdown_text = font.render(str(countdown_number), True, (0,0,0))
            text_rect = countdown_text.get_rect(center=(self.WINDOW_W // 2, self.WINDOW_H // 2))  # Center the text
            
            # Draw the countdown number on the screen
            self.screen.blit(countdown_text, text_rect)

            # Update the display
            pg.display.update()

            # Wait for a second before decreasing the countdown number
            time.sleep(1)

            # Decrease the countdown number
            countdown_number -= 1
    
        self.state = States.PLAYING

    def playing(self, event_list):
        
        # Controls in game:
        keys = pg.key.get_pressed()
        mouse_buttons = pg.mouse.get_pressed()

        if keys[pg.K_q]:
            pg.quit()
            sys.exit()
        if keys[pg.K_ESCAPE]:
            self.state = States.MENU
        
        # If the player controlled units list is empty we dont take inputs
        if self.units_player_controlled:
            if keys[pg.K_a]:
                self.units_player_controlled[0].rotate(-1)
            if keys[pg.K_d]:
                self.units_player_controlled[0].rotate(1)
            if keys[pg.K_w]:
                self.units_player_controlled[0].move("forward")
            if keys[pg.K_s]:
                self.units_player_controlled[0].move("backward")
            if keys[pg.K_SPACE] or mouse_buttons[0]:
                self.units_player_controlled[0].shoot()
                
            if keys[pg.K_p]:
                print(f"{self.show_pathfinding_paths=}")
                mouse_pos = pg.mouse.get_pos()  # Mouse position
                top_left_corner = self.border_polygon[3]    # Top left corner of map
                
                # Only start a path search/init if the grid_dict is present
                if self.grid_dict is not None:
                    self.units_player_controlled[0].init_waypoint(self.grid_dict, mouse_pos, top_left_corner, self.node_spacing)
                # -------------------------------------------
                # Alt under er blot test og skal ikke finde sted her. Skal rettes
                # Dette kunne laves sådan den opdaterer path og fjerner nodes.
                # Dette vil kræve at man konstant kigger efter alle units waypoint queues ligesom under, udover
                # Det skal ske hver frame og ikke kun når der trykkes på p
                if self.show_pathfinding_paths:
                    
                    self.all_unit_waypoint_queues.clear()

                    # Get all waypoint queues from all units
                    for unit in self.units:
                        waypoint_queue = unit.get_waypoint_queue()
                        print(f"Waypoint queue: {waypoint_queue}")
                    
                        if waypoint_queue != None:
                            # Convert waypoint queue to a list of lines to be drawn
                            path_lines = [(waypoint_queue[i], waypoint_queue[i + 1]) for i in range(len(waypoint_queue) - 1)]
                            
                            self.all_unit_waypoint_queues.append(path_lines)
                        
                        print(f"All waypoint paths: {self.all_unit_waypoint_queues}")
                    else:
                        print(f"self.grid is None")
                # -------------------------------------------
        self.update()
        self.draw()

    
    # ==================== Shared button handler for states ====================
    
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
            
    # ============================================ ------------- ============================================
    # ============================================ ------------- ============================================

    def handle_events(self, event_list):
        """Handle player inputs and game events."""

        for event in event_list:
            match event.type:
                case pg.QUIT:
                    pg.quit()
                    sys.exit()
                case pg.KEYDOWN:
                    if event.key == pg.K_r:
                        print("RESPAWN")
                        self.units[0].respawn() # The 0 indicates player tank
            
            # ----------------------------------------- ctrl-f (Test MED DETECT)-----------------------
            if event.type == pg.MOUSEBUTTONUP:
                pos = pg.mouse.get_pos()
                for poly in self.polygon_list_no_border:

                    poly_pg_object = pg.draw.polygon(self.screen, (0,100,0), poly)
                    if poly_pg_object.collidepoint(pos):
                        print("True mouse inside polygone")
            # ----------------------------------------- ctrl-f (Test MED DETECT)-----------------------
            
    def update(self):
        
        # Temp list is created and all units projectiles are added to a single list
        temp_projectiles= []
        for unit in self.units:
            # Add projectiles from this unit to the list
            temp_projectiles.extend(unit.get_projectile_list())
            
        # The temp list is all active projetiles
        self.projectiles = temp_projectiles
        
        #Update game state: projectiles, units, and collisions.
        # Update all projectiles from all tanks
        for unit in self.units:
            for i, proj in enumerate(unit.get_projectile_list()):
                for obstacle in self.obstacles:
                    for corner_pair in obstacle.get_corner_pairs():
                        proj.collision(corner_pair)
                
                # For each projectile from unit, we check if it hits any other_unit and remove it if it hits
                projectile_line = proj.get_line()
                for other_unit in self.units:
                    
                    # Make sure to skip dead units (makes projectiles pass through dead tanks)
                    if other_unit.get_death_status():
                        continue
                    if other_unit.collision(projectile_line, collision_type="projectile"):
                        if unit.projectiles:
                            unit.projectiles.pop(i)

                proj.update()

        # Remove dead projectiles
        self.projectiles[:] = [p for p in self.projectiles if p.alive]

        # Check unit/surface collisions
        for unit in self.units:
            for obstacle in self.obstacles:
                for corner_pair in obstacle.get_corner_pairs():
                    unit.collision(corner_pair, collision_type="surface")
            
            # Check for unit unit collision 
            for other_unit in self.units:
                if other_unit == unit:
                    continue
                if not self.are_tanks_close(unit, other_unit):
                    continue
                if other_unit.get_death_status():
                    continue
                
                #front_cornerpairs = other_unit.get_hitbox_corner_pairs()[1:2][0] - front
                for other_corner_pair in other_unit.get_hitbox_corner_pairs():
                    unit.collision(other_corner_pair, collision_type="surface")
                    
                    other_unit.add_direction_vector(unit.get_direction_vector())
                # SKAL RETTES
                # Next add so that you direction vector gets added to theirs
                
            
            
    def are_tanks_close(self, tank1: Tank, tank2: Tank, threshold=50) -> bool:
        """Proximity check: if tanks' centers are close enough based on their radius."""
        # Get the center coordinates of both tanks
        x1, y1 = tank1.get_pos()  # Assuming get_pos() returns the center (x, y)
        x2, y2 = tank2.get_pos()

        # Calculate the distance between the two centers
        distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Check if the distance is less than or equal to the threshold (radius)
        return distance <= threshold  
    
    def are_projectile_close_surface(self, projectile, obstacle):
        pass
        #x1, y1 = projectile.get_pos()
        # Skal rettes
        # Optimering ide hvor man ikke regner line intersect for alle object, men kun for dem der inden for
        # en radius af projectile. Dette er dog ligt svært når obstacles er linjer?
        


    def draw(self):
        """Render all objects on the screen."""
        self.display.fill("white")
        self.screen.blit(pg.transform.scale(self.display, self.WINDOW_DIM), (0, 0))

        for unit in self.units:
            unit.draw(self.screen)
        
        for proj in self.projectiles:
            proj.draw(self.screen)

        for obstacle in self.obstacles:
            # Debug: draw obstacle collision lines
            for corner_pair in obstacle.get_corner_pairs():
                pg.draw.line(self.screen, "red", corner_pair[0], corner_pair[1], 3)
                
                # Draw corners of obstacles if turned on
                if self.show_obstacle_corners:
                    pg.draw.circle(self.screen, "blue", center=corner_pair[0], radius=5)   

        # If path finding visuals is on draw path lines and nodes:
        if self.show_pathfinding_nodes:
            for node in self.valid_nodes:
                pg.draw.circle(self.screen, "purple", node, 5)  # Draw nodes as circles
                
        # Draw path
        if self.show_pathfinding_paths:
            for queue in self.all_unit_waypoint_queues:
                for c1, c2 in queue:
                    pg.draw.line(self.screen, "green", c1, c2, 5)  # Already converted to Pygame
        
        self.render_debug_info()

        pg.display.update()
        self.clock.tick(self.fps)   # Controls FPS


            
    def render_debug_info(self):
        """Render debug information on the right-side bar."""
        font = pg.font.Font(None, 24)  # Default font, size 24
        debug_text = [
            f"FPS: {self.clock.get_fps():.2f}",
            f"Active projectiles: {len(self.projectiles)}",
            f"Main tank angle: {self.units[0].degrees}"
        ]

        # Start position for text
        x_start = self.WINDOW_DIM[0] - 190  
        y_start = 10  

        for text in debug_text:
            text_surface = font.render(text, True, (0, 0, 0))  # White text
            self.screen.blit(text_surface, (x_start, y_start))
            y_start += 25  # Spacing between lines
            


class States:
    MENU = "menu"
    SETTINGS = "settings"
    LEVEL_SELECT = "level_select"
    PLAYING = "playing"
    COUNTDOWN = "countdown"
    EXIT = "exit"
