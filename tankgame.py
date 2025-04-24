
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
        # self.last_frame_time = pg.time.get_ticks() / 1000  # Convert to seconds immediately
        self.fps = 100
        
        #self.dpi_fix()

        # Window setup
        self.WINDOW_DIM = self.WINDOW_W, self.WINDOW_H = 1980, 1200
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
        
        self.obstacles_sta: list[Obstacle] = [] # standard
        self.obstacles_des: list[Obstacle] = [] # destructible
        self.obstacles_pit: list[Obstacle] = [] # pit
        self.obstacles_ai:  list[Obstacle] = [] # destructible + standard (changes based on whats destroyed)
        self.prev_obstacles_des:  list[Obstacle] = [] # Store previous frame des data
        
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
        self.cap_fps = True

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
        self.active_mine_explosions = []
        
        self.delta_time = 1
        self.old_delta_time = 1
        self.time = 0
        self.last_print_time = 0
        self.fps_list = []
        self.delta_time_list = []
        
        self.update_des_flag = False    # flag that updates des obstacles
        
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
   
    def wrap_texture_on_polygons_static(self, polygons_data_list: list, texturing_dict: dict) -> None:
        """Takes a list of polygons with types and assigns appropriate textures to them

        Args:
            polygons_data_list: List of tuples containing (polygon_points, polygon_type)
            texturing_dict: Dictionary mapping types to lists of images (e.g., {0: [img1, img2], 1: [img3, img4]})
        """
        dim = self.WINDOW_DIM

        # Create final texture surface
        final_texture_surface = pg.Surface(dim, pg.SRCALPHA)
        final_texture_surface.fill((0, 0, 0, 0))  # Start with transparent

        # Process each polygon type separately
        for polygon_type, texture_list in texturing_dict.items():
            # Create a surface for this type's polygons
            type_surface = pg.Surface(dim, pg.SRCALPHA)
            type_surface.fill((0, 0, 0, 0))
            
            # Create a mask surface for this type
            mask_surface = pg.Surface(dim, pg.SRCALPHA)
            mask_surface.fill((0, 0, 0, 0))
            
            # Draw all polygons of this type on the mask
            for polygon_points, p_type in polygons_data_list:
                if p_type == polygon_type:
                    pg.draw.polygon(mask_surface, (255, 255, 255, 255), polygon_points)
            
            # Create mask from the drawn polygons
            mask = pg.mask.from_surface(mask_surface)
            mask_surface = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
            
            # Create texture for this type
            texture_surface = pg.Surface(dim, pg.SRCALPHA)
            texture_surface.fill((0, 0, 0, 0))
            
            # Get all polygons of this type to find bounding area
            type_polygons = [points for points, p_type in polygons_data_list if p_type == polygon_type]
            if not type_polygons:
                continue
                
            # Get combined bounding rect for efficiency
            all_points = [point for poly in type_polygons for point in poly]
            min_x = min(p[0] for p in all_points)
            max_x = max(p[0] for p in all_points)
            min_y = min(p[1] for p in all_points)
            max_y = max(p[1] for p in all_points)
            
            # Tile textures only within the bounding area
            texture = random.choice(texture_list)
            tex_width, tex_height = texture.get_size()
            
            for x in range(int(min_x), int(max_x) + tex_width, tex_width):
                for y in range(int(min_y), int(max_y) + tex_height, tex_height):
                    texture_surface.blit(random.choice(texture_list), (x, y))
            
            # Apply mask to this type's texture
            texture_surface.blit(mask_surface, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
            
            # Combine with final texture
            final_texture_surface.blit(texture_surface, (0, 0))

        self.texture_surface = final_texture_surface

        pg.image.save(self.texture_surface, "debug_texture_output.png")


    def wrap_texture_on_polygon_type(self, obstacle_list: list, images_list) -> None:
            """Takes a list of polygons and assigns textures to them"""
            
            # Load texture and prepare it
            # texture = pg.image.load(texture_path).convert()
            # texture = pg.transform.scale(texture, (500, 150))  # scale to approximate size
            
            # Convert obstacles list to a list of list of corners
            polygons_points_list = [obstacle.corners for obstacle in obstacle_list]
            
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
            return texture_surface


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
            Button(left, 850, 300, 60, "Uncap fps", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "cap_fps")),
            Textfield(left+350, 850, 300, 60, "100", on_mouse_leave_action=self.fps_button),
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
            
            # Mine image
            path_mine = os.path.join(os.getcwd(), r"units\mines", "mine1.png")
            self.mine_img = pg.image.load(path_mine).convert_alpha()
            self.mine_img = pg.transform.scale(self.mine_img, (self.WINDOW_DIM_SCALED[0],self.WINDOW_DIM_SCALED[1]))
            
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
        self.sound_effects = {
            "cannon": [],
            "death": [],
            "wallhit": [],
            "proj_explosion": []
        }

        for i in range(1, 5):
            sound = pg.mixer.Sound(os.path.join(os.getcwd(), "sound_effects", "cannon", f"cannon{i}.mp3"))
            sound.set_volume(0.1)
            self.sound_effects["cannon"].append(sound)

        for i in range(1, 5):
            sound = pg.mixer.Sound(os.path.join(os.getcwd(), "sound_effects", "death", f"death{i}.mp3"))
            sound.set_volume(0.2)
            self.sound_effects["death"].append(sound)

        for i in range(1, 6):
            sound = pg.mixer.Sound(os.path.join(os.getcwd(), "sound_effects", "wallhit", f"hit{i}.mp3"))
            sound.set_volume(0.02)
            self.sound_effects["wallhit"].append(sound)

        for i in range(1, 7):
            sound = pg.mixer.Sound(os.path.join(os.getcwd(), "sound_effects", "proj_explosion", f"projexp{i}.mp3"))
            sound.set_volume(0.1)
            self.sound_effects["proj_explosion"].append(sound)

    
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
        self.polygon_list, self.polygons_with_type, unit_list, self.node_spacing = helper_functions.load_map_data(map_path)

        # Skal RETTES: Store polygon corners for detection (this is currently not used, just a test) ctrl-f (Test MED DETECT)
        self.polygon_list_no_border = self.polygon_list.copy()
        self.border_polygon = self.polygon_list_no_border.pop(0)    # Removes the border polygon and store seperate
        
        self.polygons_with_type_no_border = self.polygons_with_type.copy()
        self.polygons_with_type_no_border.pop(0)
        
        self.map_size = (self.border_polygon[1][0] - self.border_polygon[0][0], self.border_polygon[1][1] - self.border_polygon[2][1])
        
        # Get pathfinding data from map.
        self.grid_dict = pathfinding.get_mapgrid_dict(self.polygon_list.copy(), self.node_spacing)
        
        # Get valid nodes for path finding visuals
        _, self.valid_nodes = pathfinding.find_valid_nodes(self.border_polygon, self.node_spacing, self.polygon_list_no_border) 
        print(f"VALID NODES: {self.valid_nodes}")
        
        # ==================== Load map obstacles and units ====================
        for poly_corners, poly_type in self.polygons_with_type:
            
            if poly_type == 0:
                self.obstacles_sta.extend([Obstacle(poly_corners, poly_type)])
            if poly_type == 1:
                self.obstacles_des.extend([Obstacle(poly_corners, poly_type)])
            if poly_type == 2:
                self.obstacles_pit.extend([Obstacle(poly_corners, poly_type)])
        
        self.prev_obstacles_des = self.obstacles_des.copy()
        
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
            
            # TODO Tank image most be based on specific tank type! - Right know it is using the same. (the json already has a mapping for image name (could be removed, since type could be used to find correct picture))
            
            # Creating dict to store all unit relevant images
            tank_img, tank_turret_img  = self.load_unit_textures(unit_type_json_format)
            image_dict = {
                "tank_body": tank_img,
                "tank_turret": tank_turret_img,
                "death_marker": self.tank_death_img,
                "mine": self.mine_img
            }
            
            
            ai_type = specific_unit_data["ai_personality"]
                
            try:
                unit_to_add = Tank(startpos            = unit_pos,
                                    speed              = specific_unit_data["tank_speed_modifier"], 
                                    firerate           = specific_unit_data["firerate"],
                                    speed_projectile   = specific_unit_data["projectile_speed_modifier"],
                                    spawn_degress      = unit_angle,
                                    bounch_limit       = specific_unit_data["bounch_limit"] + 1,
                                    mine_limit         = specific_unit_data["mine_limit"],
                                    global_mine_list   = self.mines,
                                    projectile_limit   = specific_unit_data["projectile_limit"],
                                    images             = image_dict,
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
            
            # Create combined obstacle list for ai targeting
            self.obstacles_ai = self.obstacles_sta + self.obstacles_des
            unit.init_ai(self.obstacles_ai, self.projectiles, self.mines, ai_data)     
            
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
            
   
            texture_paths = {
                0: os.path.join(os.getcwd(), "map_files", "backgrounds", "wall_textures_sta"),
                1: os.path.join(os.getcwd(), "map_files", "backgrounds", "wall_textures_des"), 
                2: os.path.join(os.getcwd(), "map_files", "backgrounds", "wall_textures_pit")
            }
            
            self.texture_dict = {
                0: self.load_and_transform_images(texture_paths[0], scale=3),
                1: self.load_and_transform_images(texture_paths[0], scale=3),
                2: self.load_and_transform_images(texture_paths[2], scale=3)
            }
            
            # Destructibles: 
            self.images_des = self.load_and_transform_images(texture_paths[1], scale=3)
            self.des_texture_surface = self.wrap_texture_on_polygon_type(self.obstacles_des, self.images_des)
            
            # Standard and pit: 
            self.polygons_sta_pit = [(coord, p_type) for coord, p_type in self.polygons_with_type_no_border if p_type == 0 or p_type == 2]
            self.wrap_texture_on_polygons_static(self.polygons_sta_pit, self.texture_dict)
                
            # After loading and scaling all background images
            self.cached_background = pg.Surface(self.WINDOW_DIM).convert()
            self.cached_obstacles = pg.Surface(self.WINDOW_DIM).convert()
            
            # Blit backgrounds onto surface:
            self.cached_background.blit(self.background_outer, (0, 0))
            self.cached_background.blit(self.background_inner, self.border_polygon[3])  # position as needed
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
                self.update_delta_time()
                
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
            print("ESCAPE PRESSED")
            self.state = States.MENU
            return
        
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
                self.obstacles_sta.clear()
                self.obstacles_des.clear()
                self.obstacles_pit.clear()
                self.mines.clear()
                self.load_map()
                self.load_map_textures()

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

    def update_delta_time(self):
        # Delta time
        current_time = time.perf_counter()
        self.delta_time = min(current_time - self.last_frame_time, 0.1)
        self.last_frame_time = current_time
            
    def update(self):        
        
        if self.time - self.last_print_time >= 0.1:
           
            self.last_print_time = self.time  # Update last print time
            self.fps_list.append(1/self.delta_time)
            self.delta_time_list.append(self.delta_time)
            
            if len(self.fps_list) > 100:
                self.fps_list.pop(0)
                self.delta_time_list.pop(0)

            mov_avg_fps = sum(self.fps_list) / len(self.fps_list)
            mov_delta_fps = sum(self.delta_time_list) / len(self.delta_time_list)
        
            # print(f"DELTA TIME: {self.delta_time:.6f}  Moving average FPS: {mov_avg_fps:.1f} SPEED PLAYER: {self.units_player_controlled[0].speed:.5f} SPEED per sec {self.units_player_controlled[0].speed/self.delta_time:.1f} SPEED ORIGINAL {self.units_player_controlled[0].speed_original}")
           
        
        self.frame += 1
        self.time += self.delta_time
            
            
        # Debug output
        # if random.random() < 0.01:  # Print about 1% of frames to avoid spam
        #     print(f"Delta: {self.delta_time:.10f}, FPS: {1/self.delta_time:.1f} ")
        
        # Track marks logic
        self.track_counter += 60 * self.delta_time
        if self.track_counter >= self.track_interval:
            self.track_counter = 0
            for unit in self.units:
                unit.send_delta(self.delta_time) # Send delta time to tank instances
                
                if not unit.dead and unit.is_moving:
                    # Add track mark at tank's position
                    track_pos = unit.pos
                    track_angle = unit.degrees + 90
                    self.tracks.append(Track(tuple(track_pos), track_angle, self.track_img, lifetime=1/self.delta_time))
    
        # Update and remove old tracks
        self.tracks = [track for track in self.tracks if track.update(self.delta_time*60)]
        
        # Temp list is created and all units' projectiles are added to a single list
        temp_projectiles = []
        for unit in self.units:
            unit.update(self.delta_time)
            temp_projectiles.extend(unit.projectiles)

        for mine in self.mines:
            mine.update(self.delta_time)
        
        # Update projectiles and handle collisions
        for unit in self.units:
            for i, proj in enumerate(unit.projectiles):
                
                proj.set_delta_time(self.delta_time) # Send frame delta time
                proj.update()                   # Update the projectile
                
                for obstacle in self.obstacles_sta:
                    for corner_pair in obstacle.get_corner_pairs():
                        proj.collision(corner_pair)
                        
                for obstacle in self.obstacles_des:
                    for corner_pair in obstacle.get_corner_pairs():
                        proj.collision(corner_pair)
                        
                # Check projectile collision with other units
                projectile_line = proj.get_line()
                for other_unit in self.units:
                    if other_unit.dead:
                        continue  # Ignore dead units
                    
                    # # Skip unit if the projecile has been newly-fired from the same unit (prevents tank exploding itself)
                    if proj.spawn_timer > 0 and proj.id == other_unit.id:
                        continue
                    
                    if other_unit.collision(projectile_line, collision_type="projectile"):
                        proj.alive = False
                
        # Projectile/projectile collision check
        if temp_projectiles:
            projectile_positions = np.array([proj.pos for proj in temp_projectiles])
            tree = KDTree(projectile_positions)

            for i, proj in enumerate(temp_projectiles):
                neighbors = tree.query_ball_point(proj.pos, self.projectile_collision_dist)
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
                unit.ai.update_obstacles(self.obstacles_ai)
                unit.ai.projectiles = self.projectiles

            # Check unit/surface collisions
            for obstacle in self.obstacles_sta:
                for corner_pair in obstacle.get_corner_pairs():
                    unit.collision(corner_pair, collision_type="surface")
                    
            for obstacle in self.obstacles_des:
                for corner_pair in obstacle.get_corner_pairs():
                    unit.collision(corner_pair, collision_type="surface")

            for obstacle in self.obstacles_pit:
                for corner_pair in obstacle.get_corner_pairs():
                    unit.collision(corner_pair, collision_type="surface")


            # Check for unit-unit collision
            for other_unit in self.units:
                if unit == other_unit or other_unit.dead:
                    continue  # Skip self and dead units

                if not self.are_tanks_close(unit, other_unit):
                    continue  # Skip if tanks aren't close

                # Skip collision check with dead tanks
                if other_unit.dead or unit.dead:
                    continue
                
                # Push tanks when colliding
                unit.apply_repulsion(other_unit, push_strength=0.5)
                other_unit.apply_repulsion(unit, push_strength=0.5)  # Ensure symmetry
            

            # Mine logic
            for mine in self.mines:
                if mine.is_exploded:
                    self.handle_mine_explosion(mine)
                    self.handle_destruction()
                    self.mines.remove(mine)
                    self.update_des_flag = True
                mine.get_unit_list(self.units)
                mine.get_obstacles_des(self.obstacles_des)
                mine.check_for_tank(unit)


        self.projectiles = temp_projectiles
    
    
    def handle_destruction(self):
        if len(self.obstacles_des) != len(self.prev_obstacles_des):
            self.update_des_flag = True
            self.des_texture_surface = self.wrap_texture_on_polygon_type(self.obstacles_des, self.images_des)
            self.prev_obstacles_des = self.obstacles_des.copy()
            self.obstacles_ai = self.obstacles_sta + self.obstacles_des
 
    def draw(self):

        """Render all objects on the screen."""

        # Draw all static textures (backgrounds and obstacles)
        self.screen.blit(self.cached_background, (0, 0))
        
        # Re draw des obstacles if one was destroyed
        if self.update_des_flag:
            self.update_des_flag = False
        self.screen.blit(self.des_texture_surface, (0, 0))
            
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
            for obstacle in self.obstacles_sta+self.obstacles_des+self.obstacles_pit:
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
                
        # Tank explosions
        for animation in self.active_mine_explosions[:]:
            animation.play(self.screen)
            
            # Remove the animation if it's finished
            if animation.finished:
                self.active_mine_explosions.remove(animation)       
        
        
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

            
        if self.show_debug_info:
            self.render_debug_info()
            
        # self.render_debug_info()
            
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
        
    def handle_mine_explosion(self, mine: Mine) -> None:
        random.choice(self.sound_effects["death"]).play()

        animation = Animation(images=self.animations["tank_explosion"], frame_delay=5, delta_time=self.delta_time)
        animation.start(pos=mine.pos, angle=random.randint(0,360))
    
        self.active_mine_explosions.append(animation)
        
    # ================================================= Misc ===============================================   

    def render_debug_info(self):
        """Render debug information on the right-side bar."""
        
        
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
                f"Obstacles: {len(self.obstacles_sta)}",
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
        """Optimized proximity check using squared distance."""
        # Get the center coordinates of both tanks
        pos1 = tank1.pos
        pos2 = tank2.pos
        # Calculate the squared distance between the two centers (no sqrt for performance)
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return dx*dx + dy*dy <= threshold*threshold    
    
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