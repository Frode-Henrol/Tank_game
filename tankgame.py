
import sys
import pygame as pg
import numpy as np
import os
import utils.helper_functions as helper_functions
import utils.deflect as deflect
import time
from object_classes.projectile import Projectile
from object_classes.tank import Tank
from object_classes.obstacle import Obstacle
from object_classes.button import Button 
from object_classes.mine import Mine 
from object_classes.track import Track
from object_classes.animation import Animation
import json
import pathfinding
from scipy.spatial import KDTree
import random
import re
import ctypes
import cProfile
from object_classes.textfield import Textfield

class TankGame:
    def __init__(self):
        # Initialize Pygame
        pg.init()
        self.clock = pg.time.Clock()
        self.last_frame_time = pg.time.get_ticks() / 1000  # Convert to seconds immediately
        self.fps = 60
        
        #self.dpi_fix()

        # Window setup
        self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1980, 1200
        #self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1980-1980//2, 1200-1200//2
        self.SCALE = 30
        
        # Create display with VSync enabled
        # Try different display modes for best results
        display_flags = pg.DOUBLEBUF | pg.HWSURFACE
        self.screen = pg.display.set_mode(self.WINDOW_DIM, display_flags)
        # try:
        #     # First try with VSync
        #     self.screen = pg.display.set_mode(self.WINDOW_DIM, display_flags, vsync=1)
        #     print("VSync enabled successfully")
        # except:
        #     try:
        #         # Fallback to OpenGL with VSync
        #         display_flags |= pg.OPENGL
        #         self.screen = pg.display.set_mode(self.WINDOW_DIM, display_flags, vsync=1)
        #         print("Using OpenGL with VSync")
        #     except:
        #         # Final fallback
        #         self.screen = pg.display.set_mode(self.WINDOW_DIM)
        #         print("VSync not available")
        
        # self.screen = pg.display.set_mode(self.WINDOW_DIM)
        self.WINDOW_DIM_SCALED = self.WINDOW_W_SCALED, self.WINDOW_H_SCALED = int(self.WINDOW_W / (self.SCALE * 1.5)), int(self.WINDOW_H / self.SCALE)
        self.display = pg.Surface(self.WINDOW_DIM_SCALED)

        # Debug fps counter
        self.frame = 0
        self.total = 0
            
        self.last_frame_time = time.perf_counter()
            
        # Game objects
        self.units: list[Tank] = []
        self.units_player_controlled: list[Tank] = []
        
        self.projectiles: list[Projectile] = []
        self.obstacles: list[Obstacle] = []
        self.mines: list[Mine] = []
        
        # Projectile collision distance
        self.projectile_collision_dist = 10
        
        # Game states:
        self.state = States.MENU

        self.load_gui()                   
        self.load_animations_and_misc()   
        self.load_sound_effects()           
        self.load_map()                 
        self.load_map_textures()
        
        # Settings menu:
        self.show_obstacle_corners = False
        self.draw_hitbox = False # Not implemented 
        self.godmode = True    # Not used in tankgame class ATM
        self.show_pathfinding_nodes = False
        self.show_pathfinding_paths = False
        self.show_ai_debug = False
        self.show_debug_info = False
        self.cap_fps = False

        # Pathfinding
        self.all_unit_waypoint_queues = []
        
        # ====================== Visuals ==============================
        # Tank tracks
        self.tracks = []  # List to store all track marks
        self.track_interval = 8  # Add track every 10 frames
        self.track_counter = 0
        
        # Projectile/tank explosion
        self.active_proj_explosions = []
        self.active_tank_explosions = []
        
        self.delta_time = 1
        
        if self.godmode:
            self.godmode_toggle()
    
    def dpi_fix(self):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
    
  
    
    def godmode_toggle(self):
        for unit in self.units_player_controlled:
            print(f"Toggled godemode for all player tanks")
            unit.toggle_godmode()

    # ============================================ Load helper functions ============================================
    def load_and_transform_images(self, folder_path: str, scale: float = 1) -> list[pg.Surface]:
        """Load and scale all images in a folder using Pygame, sorted numerically."""
        pg.init()
        supported_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        image_list: list[pg.Surface] = []

        # Helper to extract numeric value from filename
        def extract_number(filename):
            match = re.search(r'\d+', filename)
            return int(match.group()) if match else float('inf')

        # Sort filenames by extracted number
        sorted_filenames = sorted(
            [f for f in os.listdir(folder_path) if f.lower().endswith(supported_exts)],
            key=extract_number
        )

        for filename in sorted_filenames:
            track_path = os.path.join(folder_path, filename)
            try:
                track_img = pg.image.load(track_path).convert_alpha()
                
                scaled_img = pg.transform.scale(track_img, (self.WINDOW_DIM_SCALED[0]*scale, self.WINDOW_DIM_SCALED[1]*scale))
                image_list.append(scaled_img)
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

        return image_list
    
    def wrap_texture_on_polygons(self, polygons_points_list: list, images_list) -> None:
        """Takes a list of polygons and assigns textures to them"""
        
        # Load texture and prepare it
        # texture = pg.image.load(texture_path).convert()
        # texture = pg.transform.scale(texture, (500, 150))  # scale to approximate size

        texture = random.choice(images_list)
        
        dim = self.WINDOW_DIM
        
        # Create a surface for all polygons
        polygon_surface = pg.Surface(dim, pg.SRCALPHA)
        polygon_surface.fill((0, 0, 0, 0))  # Fill the surface with transparency

        # Draw all polygons on the surface
        for polygon_points in polygons_points_list:
            pg.draw.polygon(polygon_surface, (255, 255, 255, 255), polygon_points)

        # Use the polygon_surface as a mask
        mask = pg.mask.from_surface(polygon_surface)
        mask_surface = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))

        # Prepare texture surface to match size
        texture_surface = pg.Surface(dim, pg.SRCALPHA)
        for x in range(0, dim[0], texture.get_width()):
            texture = random.choice(images_list)
            for y in range(0, dim[1], texture.get_height()):
                texture_surface.blit(texture, (x, y))

        # Apply mask to texture
        texture_surface.blit(mask_surface, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        self.texture_surface = texture_surface
        
        pg.image.save(self.texture_surface, "debug_texture_output.png")
    # ===============================================================================================================
    # ============================================ Load helper functions ============================================
    def load_gui(self) -> None:
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
            Button(left, 350, 300, 60, "Godmode", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:(helper_functions.toggle_bool(self, "godmode"), self.godmode_toggle())),
            Button(left, 450, 300, 60, "Show pathfinding nodes", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_pathfinding_nodes")),
            Button(left, 550, 300, 60, "Show pathfinding paths", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_pathfinding_paths")),
            Button(left, 650, 300, 60, "Show ai debug", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_ai_debug")),
            Button(left, 750, 300, 60, "Show debug info", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_debug_info")),
            Button(left, 850, 300, 60, "Cap fps", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "cap_fps")),
            Textfield(left+350, 850, 300, 60, "60", on_mouse_leave_action=self.fps_button),
            Button(left, 950, 300, 60, "Back", States.MENU)
        ]
        
        
        self.level_selection_buttons = [
            Button(left, 150, 300, 60, "Level 1", States.PLAYING),
            Button(left, 250, 300, 60, "Level 2", States.PLAYING),
            Button(left, 350, 300, 60, "Level 3", States.PLAYING),
            Button(left, 450, 300, 60, "Level 4", States.PLAYING),
            Button(left, 550, 300, 60, "Back", States.MENU)  
        ]  
        
        
    def fps_button(self):
        if self.cap_fps:
            self.clear_all_projectiles()
            self.fps = int(self.setting_buttons[8].get_string()) # Skal rettes til dict! Nurværende løsning ikke robust

            
    
    def load_animations_and_misc(self) -> None:
        """Loads animations and shared textures images"""
        try:
            # Death image
            path_tank_death = os.path.join(os.getcwd(), r"units\death_images", "tank_death3.png")
            self.tank_death_img = pg.image.load(path_tank_death).convert_alpha()
            self.tank_death_img = pg.transform.scale(self.tank_death_img, (self.WINDOW_DIM_SCALED[0],self.WINDOW_DIM_SCALED[1]))
            
            # Track image
            track_path = os.path.join(os.getcwd(),r"units\images", f"track.png")
            track_img = pg.image.load(track_path).convert_alpha()
            self.track_img = pg.transform.scale(track_img, self.WINDOW_DIM_SCALED)
            
            # Animations
            animation_path = os.path.join(os.getcwd(),"units","animations")
            self.animations = {}
            
            # Load muzzle animation
            muzzle_flash_path = os.path.join(animation_path, "muzzle_flash")
            self.muzzle_flash_list = self.load_and_transform_images(muzzle_flash_path)
            self.animations["muzzle_flash"] = self.muzzle_flash_list

            # Load projectile explosion animation
            proj_explosion_path = os.path.join(animation_path, "proj_explosion")
            self.proj_explosion_list = self.load_and_transform_images(proj_explosion_path)
            self.animations["proj_explosion"] = self.proj_explosion_list
            
            # Load projectile explosion animation (shares proj_explosion just scaled)
            self.tank_explosion_list = self.load_and_transform_images(proj_explosion_path, scale=3)
            self.animations["tank_explosion"] = self.tank_explosion_list
        except FileNotFoundError:
            print("Error: Image not found! Check your path.")
            sys.exit()
        
 
        for unit in self.units:
            unit.init_animations(self.animations)
        
    def load_sound_effects(self) -> None:
        
        pg.mixer.set_num_channels(64)
        self.sound_effects = []
        for i in range(1,5):
            cannon_sound = pg.mixer.Sound(os.path.join(os.getcwd(),"sound_effects","cannon",f"cannon{i}.mp3"))
            cannon_sound.set_volume(0.1)  # Range: 0.0 to 1.0
            self.sound_effects.append(cannon_sound)
        
        for i in range(1,5):
            death_sounds = pg.mixer.Sound(os.path.join(os.getcwd(),"sound_effects","death",f"death{i}.mp3"))
            death_sounds.set_volume(0.2)  # Range: 0.0 to 1.0
            self.sound_effects.append(death_sounds)
        
        for i in range(1,6):
            hit_sound = pg.mixer.Sound(os.path.join(os.getcwd(),"sound_effects","wallhit",f"hit{i}.mp3"))
            hit_sound.set_volume(0.02)  # Range: 0.0 to 1.0
            self.sound_effects.append(hit_sound)
            
        for i in range(1,7):
            projexp_sound = pg.mixer.Sound(os.path.join(os.getcwd(),"sound_effects","proj_explosion",f"projexp{i}.mp3"))
            projexp_sound.set_volume(0.1)  # Range: 0.0 to 1.0
            self.sound_effects.append(projexp_sound)
            
        self.projexp_sounds = self.sound_effects[13:19]
    
    def load_unit_textures(self, name: str) -> list:
        """Loads specific body and turret images for a given tank"""
        try:
            path_tank = os.path.join(os.getcwd(),r"units\images", f"{name}.png")
            turret_name = name.split("_")[0]
            path_tank_turret = os.path.join(os.getcwd(),r"units\images", f"{turret_name}_turret.png")
            
            tank_img = pg.image.load(path_tank).convert_alpha()
            tank_img = pg.transform.scale(tank_img, self.WINDOW_DIM_SCALED)
            
            tank_turret_img = pg.image.load(path_tank_turret).convert_alpha()
            tank_turret_img = pg.transform.scale(tank_turret_img, (self.WINDOW_DIM_SCALED[0]*0.5, self.WINDOW_DIM_SCALED[1]*2))
            
            return [tank_img, tank_turret_img]
    
        except FileNotFoundError:
            print("Error: Image not found! Check your path.")
            sys.exit()
        
    def load_map(self, map_path: str = r"map_files\map_test1.txt") -> None:
        """Loads data from a map file"""
        
        # ==================== Load map  ====================
        # Map data i a tuple, where 1 entre is the polygon defining the map border the second is a list of all polygon cornerlists
        self.polygon_list, unit_list, self.node_spacing = helper_functions.load_map_data(map_path)
       
        # Skal RETTES: Store polygon corners for detection (this is currently not used, just a test) ctrl-f (Test MED DETECT)
        self.polygon_list_no_border = self.polygon_list.copy()
        self.border_polygon = self.polygon_list_no_border.pop(0)    # Removes the border polygon and store seperate
        
        self.map_size = (self.border_polygon[1][0] - self.border_polygon[0][0], self.border_polygon[1][1] - self.border_polygon[2][1])
        
        # Get pathfinding data from map.
        self.grid_dict = pathfinding.get_mapgrid_dict(self.polygon_list.copy(), self.node_spacing)
        
        # Get valid nodes for path finding visuals
        _, self.valid_nodes = pathfinding.find_valid_nodes(self.border_polygon, self.node_spacing, self.polygon_list_no_border) 
        print(f"VALID NODES: {self.valid_nodes}")
        
        # ==================== Load map obstacles and units ====================
        for polygon_conrners in self.polygon_list:
            self.obstacles.extend([Obstacle(polygon_conrners)])
        
        # Tank mappings dict (maps a number to the json name, since map_files use number to store tank type, Could be done with list also, since tank numbering is 0-index)
        tank_mappings = {0 : "player_tank", 1 : "brown_tank", 2 : "ash_tank", 3 : "marine_tank", 4 : "yellow_tank", 5 : "pink_tank", 6 : "green_tank", 7 : "violet_tank", 8 : "white_tank", 9 : "black_tank"}
        
        # Load ai config
        with open(r"units\ai.json", 'r') as json_file:
            all_ai_data_json: dict = json.load(json_file)
        
        # Load unit config
        with open(r"units\units.json", "r") as json_file:
            all_units_data_json: dict = json.load(json_file)
        
        # Unpack each unit map data
        for unit in unit_list:
            unit_pos, unit_angle, unit_type, unit_team = unit
            
            # Get unit type in json format
            unit_type_json_format = tank_mappings[unit_type]
            
            # Fetch specific unit data 
            specific_unit_data = all_units_data_json[unit_type_json_format]
            
            temp_speed = 144 / self.fps 
            # TODO Tank image most be based on specific tank type! - Right know it is using the same. (the json already has a mapping for image name (could be removed, since type could be used to find correct picture))
            
            ai_type = specific_unit_data["ai_personality"]
                
            try:
                unit_to_add = Tank(startpos            = unit_pos,
                                    speed              = temp_speed * specific_unit_data["tank_speed_modifier"], 
                                    firerate           = specific_unit_data["firerate"],
                                    speed_projectile   = temp_speed * specific_unit_data["projectile_speed_modifier"],
                                    spawn_degress      = unit_angle,
                                    bounch_limit       = specific_unit_data["bounch_limit"] + 1,
                                    mine_limit         = specific_unit_data["mine_limit"],
                                    global_mine_list   = self.mines,
                                    projectile_limit   = specific_unit_data["projectile_limit"],
                                    images             = self.load_unit_textures(unit_type_json_format),
                                    death_image        = self.tank_death_img,
                                    use_turret         = True,
                                    team               = unit_team,    
                                    ai_type            = ai_type
                                    )
                
                # Init waypoint processing for tank
                unit_to_add.init_waypoint(self.grid_dict, self.border_polygon[3], self.node_spacing, self.valid_nodes)
            
                self.units.append(unit_to_add)
                    
            except Exception as e:
                print(f"Error: {e}")
            
        for unit in self.units:
            unit.set_units(self.units)  # Transfer unit list data to each tank
            
            # Get specific data for the choosen ai
            ai_data = all_ai_data_json.get(unit.ai_type)
            print(f"Choosen ai: {unit.ai_type}")
            
            unit.init_ai(self.obstacles, self.projectiles, self.mines, ai_data)     
            
            if unit.ai_type == "player":
                self.units_player_controlled.append(unit)
                
            unit.init_sound_effects(self.sound_effects)
            unit.init_animations(self.animations)
        
        print(f"Units loaded: {len(self.units)} where {len(self.units_player_controlled)} are player controlled.")  
        print(f"Player controlled units: {self.units_player_controlled[0]}")

    def load_map_textures(self) -> None:
        """Load and scale game assets (e.g., images)."""
        try:
            path = os.path.join(os.getcwd(), "map_files", "backgrounds","dessert3.png")
            self.background_inner = pg.image.load(path).convert_alpha()
            self.background_inner = pg.transform.scale(self.background_inner, self.map_size)
            
            path = os.path.join(os.getcwd(), "map_files", "backgrounds","outer_background.png")
            self.background_outer = pg.image.load(path).convert_alpha()
            self.background_outer = pg.transform.scale(self.background_outer, self.WINDOW_DIM)
            
            path = os.path.join(os.getcwd(), "map_files", "backgrounds","wall_textures")
            image_list = self.load_and_transform_images(path, scale=3)
            self.wrap_texture_on_polygons(self.polygon_list_no_border, image_list)
                
            # After loading and scaling all background images
            self.cached_background = pg.Surface(self.WINDOW_DIM).convert()

            # Blit static background layers ONCE into cached surface
            self.cached_background.blit(self.background_outer, (0, 0))
            self.cached_background.blit(self.background_inner, self.border_polygon[3])  # position as needed

            # Optional: If self.texture_surface is also static
            self.cached_background.blit(self.texture_surface, (0, 0))
                            
                
        except FileNotFoundError:
            print("Error: Image not found! Check your path.")
            sys.exit()  
            

    # ============================================ Run loop states ==========================================
    def run(self):
        """Main game loop."""
        profiler = cProfile.Profile()
        profiler.enable()
        try:
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
        finally:
            profiler.disable()
            profiler.dump_stats('game_profile.prof')

    # ============================================ State methods ============================================
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
        mouse_pos = pg.mouse.get_pos()  # Mouse position
        
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
            if mouse_buttons[0]:
                self.units_player_controlled[0].shoot(mouse_pos)
            if keys[pg.K_SPACE]:
                self.units_player_controlled[0].lay_mine()
                
            if keys[pg.K_p]:
                print(f"{self.show_pathfinding_paths=}")
                # Only start a path search/init if the grid_dict is present
                if self.grid_dict is not None:
                    self.units_player_controlled[0].find_waypoint(mouse_pos)

            if keys[pg.K_o]:
                self.units_player_controlled[0].abort_waypoint()
                
            if keys[pg.K_f]:
                self.units_player_controlled.clear()
                self.units.clear()
                self.obstacles.clear()
                self.mines.clear()
                self.load_map()

                    
                # -------------------------------------------
        self.update()
        self.draw()

    # ============================================ Handle methods ============================================
    
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
                        self.units_player_controlled[0].respawn() # The 0 indicates player tank
            
            # ----------------------------------------- ctrl-f (Test MED DETECT)-----------------------
            if event.type == pg.MOUSEBUTTONUP:
                pos = pg.mouse.get_pos()
                for poly in self.polygon_list_no_border:

                    poly_pg_object = pg.draw.polygon(self.screen, (0,100,0), poly)
                    if poly_pg_object.collidepoint(pos):
                        print("True mouse inside polygone")
            # ----------------------------------------- ctrl-f (Test MED DETECT)-----------------------
            
    # ============================================ Drawing/update ============================================     

            
    def update(self):

        # Delta time
        current_time = time.perf_counter()
        delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        self.delta_time = delta_time
        
        # Prevent absurd movement speed at loadin
        if self.delta_time > 0.01:
            self.delta_time = 0.01
            
        # Debug output
        if random.random() < 0.01:  # Print about 1% of frames to avoid spam
            print(f"Delta: {self.delta_time:.10f}, FPS: {1/self.delta_time:.1f}")
        
        # Track marks logic
        self.track_counter += 60 * self.delta_time
        if self.track_counter >= self.track_interval:
            self.track_counter = 0
            for unit in self.units:
                unit.send_delta(delta_time) # Send delta time to tank instances
                
                if not unit.dead and unit.is_moving:
                    # Add track mark at tank's position
                    track_pos = unit.get_pos()
                    track_angle = unit.degrees + 90
                    self.tracks.append(Track(tuple(track_pos), track_angle, self.track_img, lifetime=50*60*delta_time))
    
        # Update and remove old tracks
        self.tracks = [track for track in self.tracks if track.update(self.delta_time*60)]
        
        # Temp list is created and all units' projectiles are added to a single list
        temp_projectiles = []
        for unit in self.units:
            temp_projectiles.extend(unit.projectiles)

        # Update projectiles and handle collisions
        for unit in self.units:
            for i, proj in enumerate(unit.projectiles):
                
                proj.set_delta_time(delta_time) # Send frame delta time
                proj.update()                   # Update the projectile
                
                for obstacle in self.obstacles:
                    for corner_pair in obstacle.get_corner_pairs():
                        proj.collision(corner_pair)
                        
                # Check projectile collision with other units
                projectile_line = proj.get_line()
                for other_unit in self.units:
                    if other_unit.get_death_status():
                        continue  # Ignore dead units

                    if other_unit.collision(projectile_line, collision_type="projectile"):
                        proj.alive = False
                
        # Optimize projectile proximity checks with KDTree
        if temp_projectiles:
            projectile_positions = np.array([proj.get_pos() for proj in temp_projectiles])
            tree = KDTree(projectile_positions)


            for i, proj in enumerate(temp_projectiles):
                neighbors = tree.query_ball_point(proj.get_pos(), self.projectile_collision_dist)
                for j in neighbors:
                    if i != j:  # Avoid self-collision
                        temp_projectiles[i].alive = False
                        temp_projectiles[j].alive = False

                # Check for mine hit
                for mine in self.mines:
                     if helper_functions.distance(mine.pos, proj.pos) < 10:
                        mine.explode()
                        temp_projectiles[i].alive = False

        for unit in self.units:
            # Send new projectile info to AI
            if unit.ai is not None:
                unit.ai.projectiles = self.projectiles

            # Check unit/surface collisions
            for obstacle in self.obstacles:
                for corner_pair in obstacle.get_corner_pairs():
                    unit.collision(corner_pair, collision_type="surface")

            # Check for unit-unit collision
            for other_unit in self.units:
                if unit == other_unit or other_unit.get_death_status():
                    continue  # Skip self and dead units

                if not self.are_tanks_close(unit, other_unit):
                    continue  # Skip if tanks aren't close

                # Skip collision check with dead tanks
                if other_unit.dead or unit.dead:
                    continue
                
                # Push tanks when colliding
                unit.apply_repulsion(other_unit, push_strength=0.5)
                other_unit.apply_repulsion(unit, push_strength=0.5)  # Ensure symmetry
            
            if not unit.dead:
                # Mine logic
                for mine in self.mines:          
                    if mine.is_exploded:
                        self.mines.remove(mine)
                    mine.get_unit_list(self.units)
                    mine.check_for_tank(unit)

        self.projectiles = temp_projectiles
 
    def draw(self):
        """Render all objects on the screen."""
        
        # Draw all static textures (backgrounds and obstacles)
        self.screen.blit(self.cached_background, (0, 0))
    
        # Draw tank track
        for track in self.tracks:
            track.draw(self.screen)

        # Temp way of drawning dead units first: for the future make a list with dead and alive units
        for unit in self.units:
            if unit.dead:
                unit.draw(self.screen)
                
        # Drawing mines
        for mine in self.mines:
            mine.draw(self.screen)
        
        # Draw units
        for unit in self.units:
            if unit.dead:
                continue
            unit.draw(self.screen)
            
            #Draw hitbox:
            if self.draw_hitbox:
                
                hitbox = [tuple(coord) for coord in unit.hitbox]

                for corner_pair in helper_functions.coord_to_coordlist(hitbox):
                    start = tuple(map(int, corner_pair[0]))
                    end = tuple(map(int, corner_pair[1]))
                    pg.draw.line(self.screen, "blue", start, end, 3)
                    
        
        # Draw projectiles
        for proj in self.projectiles:
            proj.draw(self.screen)
        
        
        if self.show_obstacle_corners:
            # Draw obstacles
            for obstacle in self.obstacles:
                # Debug: draw obstacle collision lines
                for corner_pair in obstacle.get_corner_pairs():
                    pg.draw.line(self.screen, "red", corner_pair[0], corner_pair[1], 3)
                    
                    # Draw corners of obstacles if turned on
                    
                    pg.draw.circle(self.screen, "blue", center=corner_pair[0], radius=5)   


        # Projectile explosions
        for animation in self.active_proj_explosions[:]:
            animation.play(self.screen)
            
            # Remove the animation if it's finished
            if animation.finished:
                self.active_proj_explosions.remove(animation)
                
        # Tank explosions
        for animation in self.active_tank_explosions[:]:
            animation.play(self.screen)
            
            # Remove the animation if it's finished
            if animation.finished:
                self.active_tank_explosions.remove(animation)        
        
        for proj in self.projectiles:
            if not proj.alive:
                self.handle_projectile_explosion(proj)
                
        for unit in self.units:
            if unit.time_of_death < 10 and unit.dead:
                self.handle_tank_explosion(unit)
        
        
        # ======================== DEBUG VISUALS ===================================
        
        # If path finding visuals is on draw path lines and nodes:
        if self.show_pathfinding_nodes:
            for node in self.valid_nodes:
                pg.draw.circle(self.screen, "purple", node, 5)  # Draw nodes as circles
                
        # Draw path
        if self.show_pathfinding_paths:
            for queue in self.all_unit_waypoint_queues:
                for c1, c2 in queue:
                    pg.draw.line(self.screen, "green", c1, c2, 5)  # Already converted to Pygame
    
                        
        # Draw pathfinding paths
        if self.show_pathfinding_paths:
            self.all_unit_waypoint_queues.clear()
            # Get all waypoint queues from all units
            for unit in self.units:
                waypoint_queue = unit.get_waypoint_queue()
                if waypoint_queue != None:
                    # Convert waypoint queue to a list of lines to be drawn
                    path_lines = [(waypoint_queue[i], waypoint_queue[i + 1]) for i in range(len(waypoint_queue) - 1)]
                    self.all_unit_waypoint_queues.append(path_lines)
                    
                    
        # Draw debug info 
        if self.show_ai_debug:
            for unit in self.units:
                if unit.ai != None:
                    # Draw turret line
                    #pg.draw.line(self.screen, "purple", unit.ai.debug_turret_v[0], unit.ai.debug_turret_v[1], 3)
                    possible_nodes = unit.ai.possible_nodes
                    if unit.ai.behavior_state == "defending":
                        for node in possible_nodes:
                            pg.draw.circle(self.screen, "orange", node, 5)  # Draw nodes as circles
                            
                    if unit.ai.behavior_state == "dodge":
                        for node in unit.ai.dodge_nodes:
                            pg.draw.circle(self.screen, "red", node, 5)  # Draw nodes as circles
                            
                    if unit.ai.unit_target_line != None:
                        pg.draw.line(self.screen, unit.ai.unit_target_line_color, unit.ai.unit_target_line[0], unit.ai.unit_target_line[1], 3)
                    
                    if unit.ai.can_shoot:
                        color = "green"
                    else:
                        color = "red"
                    
                    for line in unit.ai.ray_path:
                        pg.draw.line(self.screen, color, line[0], line[1], 3)
                        
                    pg.draw.circle(self.screen, "red", unit.ai.debug_target_pos, 5)
                    print(f"{unit.ai.debug_target_pos=}")
            
        # if self.show_debug_info:
        #     self.render_debug_info()
            
        self.render_debug_info()
            
        pg.display.update()
        if self.cap_fps:
            self.clock.tick(self.fps)   # Controls FPS
        else:
            self.clock.tick()   # Uncapped Controls FPS
    
    def handle_projectile_explosion(self, proj: Projectile) -> None:
        proj.play_explosion()   # Play sound
        
        animation = Animation(images=self.animations["proj_explosion"], frame_delay=2, delta_time=self.delta_time)
        animation.start(pos=proj.pos, angle=0)
        self.active_proj_explosions.append(animation)
        
    def handle_tank_explosion(self, unit: Tank) -> None:

        animation = Animation(images=self.animations["tank_explosion"], frame_delay=6, delta_time=self.delta_time)
        animation.start(pos=unit.pos, angle=0)
        
        self.active_tank_explosions.append(animation)
        
    # ================================================= Misc ===============================================   

    def render_debug_info(self):
        """Render debug information on the right-side bar."""
        
        self.frame += 1
        self.total  +=self.clock.get_fps()
        avg = self.total / self.frame
        
        font = pg.font.Font(None, 24)  # Default font, size 24
        if self.show_debug_info:
            debug_text = [
                f"FPS: {self.clock.get_fps():.2f}",
                f"FPS avg: {avg:.2f}",
                f"Active projectiles: {len(self.projectiles)}",
                f"Main tank angle: {self.units_player_controlled[0].degrees}",
                f"Units: {len(self.units)}",
                f"Player units: {len(self.units_player_controlled)}",
                f"Obstacles: {len(self.obstacles)}",
                f"Tank 1: {self.units[1].ai.behavior_state}",
                f"Path dist: {self.units[1].ai.dist_to_target_path}",
                f"Direct dist: {self.units[1].ai.dist_to_target_direct}",
                f"Valid nodes: {len(self.units[1].ai.valid_nodes)}",
                f"Closets proj: {self.units[1].ai.closest_projectile[1]}",
                f"Dodge cooldown: {self.units[1].ai.dodge_cooldown}",
                f"AI accu: {self.units[1].ai.update_accumulator:.5f}",
                f"Tank 1: {self.units[1].ai.salvo_cooldown:.5f}"
            ]
        else:
             debug_text = [
                f"FPS: {self.clock.get_fps():.2f}",
                f"FPS avg: {avg:.2f}"
            ]
            

        
        # Start position for text
        x_start = self.WINDOW_DIM[0] - 490  
        y_start = 200  

        for text in debug_text:
            text_surface = font.render(text, True, (0, 0, 0))  # White text
            self.screen.blit(text_surface, (x_start, y_start))
            y_start += 25  # Spacing between lines
            
    def are_tanks_close(self, tank1: Tank, tank2: Tank, threshold=40) -> bool:
        """Proximity check: if tanks' centers are close enough based on their radius."""
        # Get the center coordinates of both tanks
        pos1 = tank1.get_pos()  # Assuming get_pos() returns the center (x, y)
        pos2 = tank2.get_pos()

        # Calculate the distance between the two centers
        distance = helper_functions.distance(pos1, pos2)

        # Check if the distance is less than or equal to the threshold (radius)
        return distance <= threshold  
    
    def clear_all_projectiles(self):
        # Clear for each unit
        for unit in self.units:
            unit.projectiles.clear()
        
        # Clear global list
        self.projectiles.clear()


class States:
    MENU = "menu"
    SETTINGS = "settings"
    LEVEL_SELECT = "level_select"
    PLAYING = "playing"
    COUNTDOWN = "countdown"
    EXIT = "exit"
