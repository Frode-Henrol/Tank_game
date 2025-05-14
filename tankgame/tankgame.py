
import sys
import pygame as pg
import numpy as np
import os
import time
import json
from scipy.spatial import KDTree
import random
import re
import ctypes
import cProfile
import math

from object_classes.textfield import Textfield
from object_classes.projectile import Projectile
from object_classes.tank import Tank
from object_classes.obstacle import Obstacle
from object_classes.button import Button 
from object_classes.mine import Mine 
from object_classes.track import Track
from object_classes.animation import Animation
import utils.pathfinding as pathfinding
import utils.helper_functions as helper_functions
import tankgame.utils.networking as networking

MODULE_DIR = os.path.dirname(__file__) 
MAP_DIR = os.path.join(os.path.dirname(__file__), "map_files")

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

        # Game delta time (update time)
        self.fixed_delta_time = True # Determines if the game logic scale with fps
        self.fixed_delta_time_accumulator = 0
        self.fixed_delta_time_step = 1/100

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
          
        self.dead_enemies_before_death = set()
        self.load_map()                 
        self.load_map_textures()
        
        # Settings menu:
        self.show_obstacle_corners = False
        self.draw_hitbox = False # Not implemented 
        self.godmode = False    # Not used in tankgame class ATM
        self.show_pathfinding_nodes = False
        self.show_pathfinding_paths = False
        self.show_ai_debug = False
        self.show_debug_info = False
        self.show_ai_dodge = False
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
        
        # Infoscreen state etc
        self.just_died = False  # Control visual effects in info screen when killed in game
        
        if self.godmode:
            self.godmode_toggle()
    
        # Playthrough
        self.init_playthrough()
        self.base_path_playthrough_maps = os.path.join(MODULE_DIR, r"map_files")
        self.wait_time_original = 3 # Time in seconds which before reseting after death
        self.wait_time = 0
        self.new_life_interval = 5  # How many rounds before we get new life
        self.added_life = False
        
        control_img_path = os.path.join(MODULE_DIR,"misc_images","control_page.png")
        scale = 0.75
        self.control_img = self.load_image(control_img_path, (self.WINDOW_DIM[0]//(2*scale),self.WINDOW_DIM[1]//(2*scale)))
        
        # Multiplayer
        self.network = networking.Multiplayer()
        self.hosting_game = False
        self.joined_game = False
        self.username = f"Unknown{random.randint(0,1000)}"
    
    def init_playthrough(self):
        self.playthrough_started = False
        self.current_level_number_original = 1
        self.current_level_number = self.current_level_number_original
        self.playthrough_lives_original = 3
        self.playthrough_lives = self.playthrough_lives_original
        self.last_level = 50
        self.levels_that_gave_life = set()  # Track which levels have given a life
    
    def dpi_fix(self):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
    
    def godmode_toggle(self):
        for unit in self.units_player_controlled:
            print(f"Toggled godemode for all player tanks")
            unit.toggle_godmode()

    
    
    # ===============================================================================================================
    # ============================================ Load helper functions ============================================
    def load_gui(self) -> None:
        x_mid = self.WINDOW_DIM[0] // 2
        y_mid = self.WINDOW_DIM[1] // 2
        
        # ==================== Button for states ====================
        # Last argument for button tells the button which state it should change to
        # The whole button lists should be dictionaries instead - that for future improvement
        
        button_width = 300
        left = x_mid - button_width // 2    # The x value were button starts
        
        self.menu_buttons = [
            Button(left, 250, 300, 60, "Start game", States.CONTROL_SCREEN),
            Button(left, 350, 300, 60, "Multiplayer", States.LOBBY_MENU),
            Button(left, 450, 300, 60, "Level Select", States.LEVEL_SELECT),
            Button(left, 550, 300, 60, "Settings", States.SETTINGS_MAIN),
            Button(left, 650, 300, 60, "Quit game", States.EXIT)
        ]
        
        self.pause_menu_buttons = [
            Button(left, 250, 300, 60, "Resume", States.DELAY),
            Button(left, 350, 300, 60, "Settings", States.SETTINGS_MAIN),
            Button(left, 450, 300, 60, "Main menu", States.MENU)
        ]
        
        
        self.settings_buttons_main = [
            Button(left, 250, 300, 60, "Debug", States.SETTINGS_DEBUG),
            Button(left, 350, 300, 60, "Multiplayer", States.SETTINGS_MULTIPLAYER),
            Button(left, 450, 300, 60, "Back", action=self.settings_back_button)
        ]
        
        self.settings_buttons_multiplayer = [
            Button(left, 250, 300, 60, "Stop socket", action=lambda: self.network.stop()),
            Button(left+400, 250, 300, 60, "send_join_request to server", action=lambda: self.network.send_join_request()),
            Button(left+400, 350, 300, 60, "send_input to server", action=lambda: self.network.send_input("DORIT".encode())),
            Button(left, 350, 300, 60, "Run mp method for test", action=lambda: self.multiplayer_run()),
            Button(left, 450, 300, 60, "Back", States.SETTINGS_MAIN)
        ]
        
        left_offset = 175
        right_offset = 175
        self.settings_buttons_debug = [
            Button(left-left_offset, 250, 300, 60, "Show obstacle corners", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda: helper_functions.toggle_bool(self, "show_obstacle_corners")),
            Button(left-left_offset, 350, 300, 60, "Draw hitbox", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "draw_hitbox")),
            Button(left-left_offset, 450, 300, 60, "Show ai dodge debug", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:(helper_functions.toggle_bool(self, "show_ai_dodge"), self.godmode_toggle())),
            Button(left-left_offset, 550, 300, 60, "Show pathfinding nodes", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_pathfinding_nodes")),
            Button(left-left_offset, 650, 300, 60, "Show pathfinding paths", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_pathfinding_paths")),
            Button(left+right_offset, 250, 300, 60, "Show ai debug", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_ai_debug")),
            Button(left+right_offset, 350, 300, 60, "Show debug info", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "show_debug_info")),
            Button(left+right_offset, 450, 300, 60, "Uncap fps", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda:helper_functions.toggle_bool(self, "cap_fps")),
            Button(left+right_offset, 550, 300, 60, "Test map", States.COUNTDOWN),
            Button(left, 750, 300, 60, "Back", States.SETTINGS_MAIN)
        ]
        # Custom fps choice field removed for now:
        # Textfield(left+350, 850, 300, 60, "100", on_mouse_leave_action=self.fps_button),
        
        self.level_selection_buttons = [
            Textfield(left, 250, 300, 60, "Level num"),
            Button(left, 350, 300, 60, "Play", States.CONTROL_SCREEN, action=self.lvl_select),
            Button(left, 450, 300, 60, "Back", States.MENU)  
        ]  
        
        self.lobby_menu_buttons = [
            Button(left, 175, 300, 60, "Host Game", color_disabled = "grey", disabled=True, text_color="black"),
            Textfield(left, 250, 300, 60, "Port (default 7777)"),
            Button(left, 325, 300, 60, "Start Host", States.LOBBY_MENU_MAIN, action=self.host_game_button),
            
            Button(left, 475, 300, 60, "Join Game", color_disabled = "grey", disabled=True, text_color="black"),
            Textfield(left, 550, 300, 60, "Host ip"),
            Textfield(left, 625, 300, 60, "Port (default 7777)"),
            Button(left, 700, 300, 60, "Join Game", States.LOBBY_MENU_MAIN, action=self.join_game_button),
            
            Button(left, 850, 300, 60, "Back", States.MENU)  
        ]
        
        spacing_player = 75
        self.lobby_menu_main_buttons = [
            Button(left, 250, 300, 60, "Start Game", States.CONTROL_SCREEN),
            
            Button(left, 350, 300, 60, "Players", color_disabled = "grey", disabled=True, text_color="black"),
            Button(left, 350+spacing_player, 300, 60, "Player 1 (host)", disabled=False),
            Button(left, 350+spacing_player*2, 300, 60, "---", disabled=False),
            Button(left, 350+spacing_player*3, 300, 60, "---", disabled=False),
            
            Button(left, 850, 300, 60, "Back", States.LOBBY_MENU, action=lambda: self.shut_down_socket()) 
        ]
        
        # Buttons saved for easier access (should be dict)
        self.player1_button = self.lobby_menu_main_buttons[2]
        self.player2_button = self.lobby_menu_main_buttons[3]
        self.player3_button = self.lobby_menu_main_buttons[4]
    
    
    def lvl_select(self):
        # Get lvl num from textfield:
        lvl_num = self.level_selection_buttons[0].get_string()
        if lvl_num.isdigit():
            lvl_num_int = int(lvl_num)
            if 0 < lvl_num_int <= 50:
                self.current_level_number = lvl_num_int
        
    def fps_button(self):
        if self.cap_fps:
            self.clear_all_projectiles()
            self.fps = int(self.settings_buttons_debug[8].get_string()) # Skal rettes til dict! Nurværende løsning ikke robust            
    
    def settings_back_button(self):
        if self.playthrough_started:
            self.state = States.PAUSE_MENU
        else:
            self.state = States.MENU
            
    def host_game_button(self):
        self.hosting_game = True
        self.network.start_host(username=self.username)
        
    
    def join_game_button(self):
        self.joined_game = True
        self.network.start_client(username=self.username, host_ip="127.0.0.1")
    
    def shut_down_socket(self):
        self.hosting_game = False
        self.joined_game = False
        self.network.stop()
    
    def load_animations_and_misc(self) -> None:
        """Loads animations and shared textures images"""
        try:
            # Death image
            path_tank_death = os.path.join(MODULE_DIR, r"units\death_images", "tank_death3.png")
            self.tank_death_img = pg.image.load(path_tank_death).convert_alpha()
            self.tank_death_img = pg.transform.scale(self.tank_death_img, (self.WINDOW_DIM_SCALED[0],self.WINDOW_DIM_SCALED[1]))
            
            # Mine image
            path_mine = os.path.join(MODULE_DIR, r"units\mines", "mine1.png")
            self.mine_img = pg.image.load(path_mine).convert_alpha()
            self.mine_img = pg.transform.scale(self.mine_img, (self.WINDOW_DIM_SCALED[0],self.WINDOW_DIM_SCALED[1]))
            
            # Track image
            track_path = os.path.join(MODULE_DIR,r"units\images", f"track.png")
            track_img = pg.image.load(track_path).convert_alpha()
            self.track_img = pg.transform.scale(track_img, self.WINDOW_DIM_SCALED)
            
            # Animations
            animation_path = os.path.join(MODULE_DIR,"units","animations")
            self.animations = {}
            
            # Load muzzle animation
            muzzle_flash_path = os.path.join(animation_path, "muzzle_flash")
            self.muzzle_flash_list = self.load_and_transform_images_manuel(muzzle_flash_path)
            self.animations["muzzle_flash"] = self.muzzle_flash_list

            # Load projectile explosion animation
            proj_explosion_path = os.path.join(animation_path, "proj_explosion")
            self.proj_explosion_list = self.load_and_transform_images_manuel(proj_explosion_path)
            self.animations["proj_explosion"] = self.proj_explosion_list
            
            # Load projectile explosion animation (shares proj_explosion just scaled)
            self.tank_explosion_list = self.load_and_transform_images_manuel(proj_explosion_path, scale=3)
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
            "proj_explosion": [],
            "tracks": [],
            "buttonspress": [],
            "gainlife": [],
            "lostlife": [],
            "nextlevel": [],
            "lostgame": []
        }

        for i in range(1, 5):
            sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "cannon", f"cannon{i}.mp3"))
            sound.set_volume(0.1)
            self.sound_effects["cannon"].append(sound)

        for i in range(1, 5):
            sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "death", f"death{i}.mp3"))
            sound.set_volume(0.2)
            self.sound_effects["death"].append(sound)

        for i in range(1, 6):
            sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "wallhit", f"hit{i}.mp3"))
            sound.set_volume(0.04)
            self.sound_effects["wallhit"].append(sound)

        for i in range(1, 7):
            sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "proj_explosion", f"projexp{i}.mp3"))
            sound.set_volume(0.1)
            self.sound_effects["proj_explosion"].append(sound)
        
        
        for i in range(1, 11):
            sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "tracks", f"tracks{i}.mp3"))
            sound.set_volume(0.025)
            self.sound_effects["tracks"].append(sound)
        
        sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "ui", f"lostlife.mp3"))
        sound.set_volume(0.2)
        self.sound_effects["lostlife"].append(sound)
        
        sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "ui", f"gainlife.mp3"))
        sound.set_volume(0.2)
        self.sound_effects["gainlife"].append(sound)

        sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "ui", f"nextlevel.mp3"))
        sound.set_volume(0.2)
        self.sound_effects["nextlevel"].append(sound)
            
        sound = pg.mixer.Sound(os.path.join(MODULE_DIR, "sound_effects", "ui", f"lostgame.mp3"))
        sound.set_volume(0.2)
        self.sound_effects["lostgame"].append(sound)
                  
    def load_map(self, map_path: str =  os.path.join(MAP_DIR, r"map_test1.txt")) -> None:
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
        tank_mappings = {0 : "player_tank", 
                         1 : "brown_tank", 
                         2 : "ash_tank", 
                         3 : "marine_tank", 
                         4 : "yellow_tank", 
                         5 : "pink_tank", 
                         6 : "green_tank", 
                         7 : "violet_tank", 
                         8 : "white_tank", 
                         9 : "black_tank",
                         
                         10 : "zblue_tank",
                         11 : "zbrown_tank", 
                         12 : "zash_tank", 
                         13 : "zmarine_tank", 
                         14 : "zyellow_tank", 
                         15 : "zpink_tank", 
                         16 : "zgreen_tank", 
                         17 : "zviolet_tank", 
                         18 : "zwhite_tank", 
                         19 : "zblack_tank"
                        }
        
        # Load ai config
        with open(os.path.join(MODULE_DIR,r"units\ai.json"), 'r') as json_file:
            all_ai_data_json: dict = json.load(json_file)
        
        
        # Load unit config
        with open(os.path.join(MODULE_DIR,r"units\units.json"), "r") as json_file:
            all_units_data_json: dict = json.load(json_file)
        
        # Unpack each unit map data
        for i, unit in enumerate(unit_list):
            
            
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
                                    order_id           = i,    
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
        
        # For loop makes sure we dont respawn killed tanks from a level
        temp_units = []
        for unit in self.units:
            if unit.order_id not in self.dead_enemies_before_death:
                temp_units.append(unit)
        
        self.units = temp_units
        
        print(f"Units loaded: {len(self.units)} where {len(self.units_player_controlled)} are player controlled.")  
        print(f"Player controlled units: {self.units_player_controlled[0]}")

    # ============================================ Load helper functions ============================================
    def load_and_transform_images_manuel(self, folder_path: str, scale: float = 1) -> list[pg.Surface]:
        """Load and scale all images in a folder using Pygame, sorted numerically. 
            Manuel scale input
        """
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
            path = os.path.join(folder_path, filename)
            try:
                img = pg.image.load(path).convert_alpha()  
                scaled_img = pg.transform.scale(img, (self.WINDOW_DIM_SCALED[0]*scale, self.WINDOW_DIM_SCALED[1]*scale))
                image_list.append(scaled_img)
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

        return image_list

    def load_and_transform_images_automatic(self, folder_path: str, node_spacing: int = 50) -> list[pg.Surface]:
        """Load and scale all images in a folder using Pygame, so each image fits inside node_spacing x node_spacing.
            Scale automatic based on nodespacing
        """
        pg.init()
        supported_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        image_list: list[pg.Surface] = []

        def extract_number(filename):
            match = re.search(r'\d+', filename)
            return int(match.group()) if match else float('inf')

        sorted_filenames = sorted(
            [f for f in os.listdir(folder_path) if f.lower().endswith(supported_exts)],
            key=extract_number
        )

        for filename in sorted_filenames:
            path = os.path.join(folder_path, filename)
            try:
                img = pg.image.load(path).convert_alpha()

                width, height = img.get_size()
                scale_factor = node_spacing / max(width, height)  # <- make sure the *larger side* fits

                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)

                scaled_img = pg.transform.scale(img, (new_width, new_height))
                image_list.append(scaled_img)
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

        return image_list
   
    def wrap_texture_on_polygons_static(self, polygons_data_list: list, texturing_dict: dict) -> None:
        """Takes a list of polygons with types and assigns appropriate textures to them. Outputs several polygons types on same surface.

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

        # Output textures as image
        # pg.image.save(self.texture_surface, "debug_texture_output.png")

    def wrap_texture_on_polygon_type(self, obstacle_list: list, images_list) -> None:
            """Takes a list of polygons and assigns textures to them. ONLY used for single polygon type, like for the destructibles, that needs their own surface"""
            
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

            # Start Pattern based at top-left of map:
            topleft_x, topleft_y = self.border_polygon[3]
            
            # Prepare texture surface to match size
            texture_surface = pg.Surface(dim, pg.SRCALPHA)
            for x in range(topleft_x, dim[0], texture.get_width()):
                texture = random.choice(images_list)
                for y in range(topleft_y, dim[1], texture.get_height()):
                    texture_surface.blit(texture, (x, y))

            # Apply mask to texture
            texture_surface.blit(mask_surface, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
            return texture_surface
    
    def load_image(self, path: str, scale: tuple[float,float]):
        """Load image from path"""
        try:
            path = os.path.join(path)
            image = pg.image.load(path).convert_alpha()
            return pg.transform.scale(image, (scale[0], scale[1]))    
        except FileNotFoundError:
            print(f"Error: Image not found at {path} ! Check your path.")
            sys.exit() 
    
    def load_map_textures(self) -> None:
        """Load and scale game assets (e.g., images)."""
        try:
            path = os.path.join(MODULE_DIR, "map_files", "backgrounds","dessert3.png")
            self.background_inner = pg.image.load(path).convert_alpha()
            self.background_inner = pg.transform.scale(self.background_inner, self.map_size)
            
            path = os.path.join(MODULE_DIR, "map_files", "backgrounds","outer_background.png")
            self.background_outer = pg.image.load(path).convert_alpha()
            self.background_outer = pg.transform.scale(self.background_outer, self.WINDOW_DIM)
            
   
            texture_paths = {
                0: os.path.join(MODULE_DIR, "map_files", "backgrounds", "wall_textures_sta"),
                1: os.path.join(MODULE_DIR, "map_files", "backgrounds", "wall_textures_des"), 
                2: os.path.join(MODULE_DIR, "map_files", "backgrounds", "wall_textures_pit")
            }
            
            self.texture_dict = {
                0: self.load_and_transform_images_automatic(texture_paths[0]),
                1: self.load_and_transform_images_automatic(texture_paths[1]),
                2: self.load_and_transform_images_automatic(texture_paths[2])
            }
            
            # Destructibles: 
            self.images_des = self.texture_dict[1]
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
    
    def load_unit_textures(self, name: str) -> list:
        """Loads specific body and turret images for a given tank"""
        try:
            path_tank = os.path.join(MODULE_DIR,r"units\images", f"{name}.png")
            turret_name = name.split("_")[0]
            path_tank_turret = os.path.join(MODULE_DIR,r"units\images", f"{turret_name}_turret.png")
            
            tank_img = pg.image.load(path_tank).convert_alpha()
            tank_img = pg.transform.scale(tank_img, (self.WINDOW_DIM_SCALED[0],self.WINDOW_DIM_SCALED[1]*1.2))
            
            tank_turret_img = pg.image.load(path_tank_turret).convert_alpha()
            tank_turret_img = pg.transform.scale(tank_turret_img, (self.WINDOW_DIM_SCALED[0]*0.5, self.WINDOW_DIM_SCALED[1]*2))
            
            return [tank_img, tank_turret_img]
    
        except FileNotFoundError:
            print("Error: Image not found! Check your path.")
            sys.exit()
        
    # ============================================ Run loop states ==========================================
    def run(self):
        """Main game loop."""
        
        while True:
            
            self.update_delta_time()
            
            # Update lobby menu if host or client
            if self.hosting_game or self.joined_game:
                self.multiplayer_run_lobby()
            
            event_list = pg.event.get()
            
            if self.state == States.MENU:
                self.main_menu(event_list)
            elif self.state == States.SETTINGS_MAIN:
                self.settings_main(event_list)
            elif self.state == States.SETTINGS_DEBUG:
                self.settings_debug(event_list)
            elif self.state == States.SETTINGS_MULTIPLAYER:
                self.settings_multiplayer(event_list)
            elif self.state == States.PAUSE_MENU:
                self.pause_menu(event_list)
            elif self.state == States.PLAYTHROUGH:
                self.playthrough(event_list)
            elif self.state == States.LEVEL_SELECT:
                self.level_selection(event_list)
            elif self.state == States.LOBBY_MENU:
                self.lobby_menu(event_list)
            elif self.state == States.LOBBY_MENU_MAIN:
                self.lobby_menu_main(event_list)
            elif self.state == States.PLAYING:
                self.playing(event_list)
            elif self.state == States.COUNTDOWN:
                self.count_down(event_list)
            elif self.state == States.DELAY:
                self.delay(event_list)
            elif self.state == States.INFO_SCREEN:
                self.info_screen(event_list)
            elif self.state == States.END_SCREEN:    
                self.end_screen(event_list)
            elif self.state == States.CONTROL_SCREEN:
                self.control_screen(event_list)
            elif self.state == States.EXIT:
                self.exit()
            
            self.handle_events(event_list)
            
        # Profiler. Use snakeviz for visuals
        # profiler = cProfile.Profile()
        # profiler.enable()
        # try:
        #     insert while loop here to profile
        # finally:
        #     profiler.disable()
        #     profiler.dump_stats('game_profile.prof')
        
    
    
    # ============================================ State methods ============================================
    def main_menu(self, event_list):
        if self.playthrough_started:
            self.playthrough_started = False
            self.dead_enemies_before_death = set()
            self.clear_all_map_data()
            self.init_playthrough()
        
        self.screen.fill("gray")
        self.handle_buttons(self.menu_buttons, event_list, self.screen)
        pg.display.update()
        
    def pause_menu(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.pause_menu_buttons, event_list, self.screen)
        pg.display.update()
        
        # keys = pg.key.get_pressed()
        # if keys[pg.K_ESCAPE]:
        #     print("ESCAPE PRESSED")
        #     self.state = States.DELAY
        #     return

    def exit(self):
        pg.quit()
        sys.exit()
        
    def settings_main(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.settings_buttons_main, event_list, self.screen)
        pg.display.update()
    
    def settings_debug(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.settings_buttons_debug, event_list, self.screen)
        pg.display.update()
        
    def settings_multiplayer(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.settings_buttons_multiplayer, event_list, self.screen)
        pg.display.update()
    
    def lobby_menu(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.lobby_menu_buttons, event_list, self.screen)
        pg.display.update()
    
    def lobby_menu_main(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.lobby_menu_main_buttons, event_list, self.screen)
        pg.display.update()
    
    def playthrough(self, event_list):
        
        if self.playthrough_started == True:
            
            # If gaining life
            if (self.current_level_number % self.new_life_interval == 0 and 
                self.current_level_number not in self.levels_that_gave_life):
                self.added_life = True  # Bool for infoscreen
                self.playthrough_lives += 1
                self.levels_that_gave_life.add(self.current_level_number)  # Mark this level as having given a life
                print(f"ADDED life: {self.playthrough_lives - 1} -> {self.playthrough_lives}")
 
            # If dead
            if self.units_player_controlled[0].dead:
                print("Reseting")
                
                # Store orderIDs of dead enemies before clearing
                current_dead_enemies = {
                unit.order_id for unit in self.units 
                if unit.team != self.units_player_controlled[0].team and unit.dead
                }
                self.dead_enemies_before_death.update(current_dead_enemies)

                self.wait_time = 0
                self.playthrough_lives -= 1
                self.clear_all_map_data()
                self.start_map()
                self.state = States.INFO_SCREEN
                self.just_died = True
                print(f"Tank died life: {self.playthrough_lives} -> {self.playthrough_lives - 1}")
                return

            # If level clear
            if all(unit.dead for unit in self.units if unit.team != self.units_player_controlled[0].team):
                self.dead_enemies_before_death = set()
                self.wait_time = 0
                self.current_level_number += 1
                self.clear_all_map_data()
                if self.current_level_number > self.last_level:
                    self.state = States.END_SCREEN
                    return
                
                self.start_map()
                self.state = States.INFO_SCREEN
                print(f"Next level: {self.current_level_number-1} -> {self.current_level_number}")
                return
                    
        # When playthrough done
        if self.playthrough_started == False:
            self.playthrough_started = True
            self.clear_all_map_data()
            self.start_map()
            self.state = States.INFO_SCREEN
            return
    
    def level_selection(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.level_selection_buttons, event_list, self.screen)
        pg.display.update()
    
    def info_screen(self, event_list):
        clock = pg.time.Clock()

        lost_life = self.just_died
        gain_life = self.added_life
        # A level can both give a life AND be a level up
        level_up = self.current_level_number > 1  # Always true except first level
        
        # Determine previous values for animation
        if lost_life:
            previous_lives = self.playthrough_lives + 1  # Because we already decremented
            previous_level = self.current_level_number  # Level doesn't change when losing life
        elif gain_life:
            previous_lives = self.playthrough_lives - 1  # Because we already incremented
            previous_level = self.current_level_number - 1  # Level does increase
        else:
            previous_lives = self.playthrough_lives
            previous_level = self.current_level_number - 1

        # Special case: first level shows as 1 immediately
        if self.current_level_number == 1:
            previous_level = 1
            level_up = False

        game_over_text = "Game over"
        start_time = pg.time.get_ticks()

        if self.playthrough_lives == 0:
            duration = 7000
        else:
            duration = 4000

        flash_duration = 2000
        shake_duration = 700
        fade_in_duration = 1000
        game_over_fade_duration = 3000
        max_alpha = 255
        post_shake_red_duration = 1000
        red_fade_duration = 1000    

        next_level_sound_check = False
        gain_life_sound_check = False
        lost_life_sound_check = False
        lost_game_sound_check = False
        
        while True:
            now = pg.time.get_ticks()
            elapsed = now - start_time

            if elapsed >= duration:
                break

            self.screen.fill("black")

            # General fade in
            alpha = max_alpha if elapsed >= fade_in_duration else int((elapsed / fade_in_duration) * max_alpha)

            # Animate Lives and Level
            lives_display = previous_lives
            level_display = previous_level
            
            if elapsed > flash_duration:
                t = min(max((elapsed - flash_duration) / shake_duration, 0), 1)
                
                # Handle life changes
                if lost_life:
                    lives_display = int(previous_lives - t)  # Count down when losing life
                    level_display = previous_level  # LEVEL SHOULD NOT CHANGE WHEN DYING!
                elif gain_life:
                    lives_display = int(previous_lives + t)  # Count up when gaining life
                    if level_up:  # Only animate level if we're actually leveling up
                        level_display = int(previous_level + t)
                elif level_up:  # Normal level up without life gain
                    level_display = int(previous_level + t)
                    
                # Play sounds at start of animation
                if lost_life and not lost_life_sound_check:
                    self.sound_effects["lostlife"][0].play()
                    lost_life_sound_check = True
                if gain_life and not gain_life_sound_check and not lost_life:
                    self.sound_effects["gainlife"][0].play()
                    self.sound_effects["nextlevel"][0].play()
                    gain_life_sound_check = True
                    
            if level_up and not lost_life and not next_level_sound_check:
                self.sound_effects["nextlevel"][0].play()
                next_level_sound_check = True
                
            # Font sizes with pulse effect
            lives_font_size = 100
            level_font_size = 100
            if (lost_life or gain_life or level_up) and flash_duration < elapsed < flash_duration + shake_duration:
                pulse_progress = (elapsed - flash_duration) / shake_duration
                lives_font_size = int(100 + 30 * math.sin(pulse_progress * math.pi))
                level_font_size = int(100 + 30 * math.sin(pulse_progress * math.pi))
                
            lives_font = pg.font.Font(None, lives_font_size)
            level_font = pg.font.Font(None, level_font_size)

            # Color effects
            if lost_life and flash_duration < elapsed < flash_duration + shake_duration:
                t = (elapsed - flash_duration) / shake_duration
                lives_color = (255, int(255 - 155 * t), int(255 - 155 * t))
                level_color = (255, 255, 255)
            elif lost_life and flash_duration + shake_duration <= elapsed < flash_duration + shake_duration + post_shake_red_duration:
                lives_color = (255, 100, 100)
                level_color = (255, 255, 255)
            elif lost_life and elapsed > flash_duration + shake_duration + post_shake_red_duration:
                fade_t = min(max((elapsed - (flash_duration + shake_duration + post_shake_red_duration)) / red_fade_duration, 0), 1)
                lives_color = (255, int(100 + (255 - 100) * fade_t), int(100 + (255 - 100) * fade_t))
                level_color = (255, 255, 255)
            elif gain_life and flash_duration <= elapsed < flash_duration + shake_duration:
                t = (elapsed - flash_duration) / shake_duration
                lives_color = (int(255 - 155 * t), 255, int(255 - 155 * t))
                level_color = (255, 255, int(255 - 155 * t))
            elif gain_life and flash_duration + shake_duration <= elapsed < flash_duration + shake_duration + post_shake_red_duration:
                lives_color = (100, 255, 100)
                level_color = (255, 255, 100)
            elif gain_life and elapsed > flash_duration + shake_duration + post_shake_red_duration:
                fade_t = min(max((elapsed - (flash_duration + shake_duration + post_shake_red_duration)) / red_fade_duration, 0), 1)
                lives_color = (int(100 + (255 - 100) * fade_t), 255, int(100 + (255 - 100) * fade_t))
                level_color = (255, 255, int(100 + (255 - 100) * fade_t))
            elif level_up and flash_duration <= elapsed < flash_duration + shake_duration:
                t = (elapsed - flash_duration) / shake_duration
                level_color = (255, 255, int(255 - 155 * t))
                lives_color = (255, 255, 255)
            elif level_up and flash_duration + shake_duration <= elapsed < flash_duration + shake_duration + post_shake_red_duration:
                level_color = (255, 255, 100)
                lives_color = (255, 255, 255)
            elif level_up and elapsed > flash_duration + shake_duration + post_shake_red_duration:
                fade_t = min(max((elapsed - (flash_duration + shake_duration + post_shake_red_duration)) / red_fade_duration, 0), 1)
                level_color = (255, 255, int(100 + (255 - 100) * fade_t))
                lives_color = (255, 255, 255)
            else:
                level_color = (255, 255, 255)
                lives_color = (255, 255, 255)
                    
            # Always show at least level 1
            if self.current_level_number == 1:
                level_display = max(level_display, 1)
                    
            # Render text surfaces
            level_text_str = f"Level {level_display}"
            level_surf = level_font.render(level_text_str, True, level_color).convert_alpha()
            lives_surf = lives_font.render(f"Lives: {lives_display}", True, lives_color).convert_alpha()
        
            
            level_surf.set_alpha(alpha)
            lives_surf.set_alpha(alpha)

            # Shake effect
            offset_x = offset_y = 0
            if (lost_life or gain_life or level_up) and flash_duration < elapsed < flash_duration + shake_duration:
                offset_x = random.randint(-10, 10)
                offset_y = random.randint(-10, 10)

            # Position text
            total_width = level_surf.get_width() + 40 + lives_surf.get_width()
            x = self.WINDOW_W // 2 - total_width // 2
            y = self.WINDOW_H // 2
                
            self.screen.blit(level_surf, (x + offset_x, y + offset_y))
            self.screen.blit(lives_surf, (x + level_surf.get_width() + 40 + offset_x, y + offset_y))

            # Game Over text
            if lost_life and self.playthrough_lives == 0 and elapsed > flash_duration + shake_duration:
                t = min(max((elapsed - (flash_duration + shake_duration)) / game_over_fade_duration, 0), 1)
                game_over_alpha = int(t * max_alpha)
                game_over_font = pg.font.Font(None, 120)
                game_over_surf = game_over_font.render(game_over_text, True, (255, 0, 0)).convert_alpha()
                game_over_surf.set_alpha(game_over_alpha)
                game_over_rect = game_over_surf.get_rect(center=(self.WINDOW_W // 2, self.WINDOW_H // 2 + 120))
                self.screen.blit(game_over_surf, game_over_rect)
                
                if not lost_game_sound_check:
                    self.sound_effects["lostgame"][0].play()
                    lost_game_sound_check = True

            pg.display.update()
            clock.tick(60)

        self.added_life = False
        self.just_died = False

        if self.playthrough_lives == 0:
            self.state = States.MENU
            self.clear_all_map_data()
            self.init_playthrough()
        else:
            self.state = States.COUNTDOWN

    def end_screen(self, event_list):
        font = pg.font.SysFont(None, 100)
        text_surface = font.render("You won", True, (255, 255, 255))
        text_surface = text_surface.convert_alpha()
        self.dead_enemies_before_death = set()

        start_time = pg.time.get_ticks()
        duration = 8000  # total screen duration in ms
        fade_duration = 2000  # duration of fade-in effect

        while True:
            now = pg.time.get_ticks()
            elapsed = now - start_time

            if elapsed >= duration:
                break

            # Calculate fade-in alpha
            if elapsed < fade_duration:
                alpha = int((elapsed / fade_duration) * 255)
            else:
                alpha = 255

            # Apply alpha to text
            text_surface.set_alpha(alpha)

            # Fill and draw
            self.screen.fill("black")
            text_rect = text_surface.get_rect(center=self.screen.get_rect().center)
            self.screen.blit(text_surface, text_rect)

            pg.display.update()
            pg.time.delay(30)

        self.state = States.MENU
        
    def count_down(self, event_list):
        # Set countdown starting number (for example, 3 seconds)
        countdown_number = 3
        
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
    
    def control_screen(self, event_list):
        # Calculate centered position
        img_width, img_height = self.control_img.get_size()
        x_pos = (self.WINDOW_W - img_width) // 2
        y_pos = (self.WINDOW_H - img_height) // 2
        
        # Create copy for alpha manipulation
        fade_img = self.control_img.copy()
        alpha = 0  # Start fully transparent
        fade_speed = 5
        fade_phase = "in"  # "in", "hold", or "out"
        
        clock = pg.time.Clock()
        running = True
        
        while running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    exit()
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_RETURN and fade_phase == "hold":
                        fade_phase = "out"
            
            # Handle fade phases
            if fade_phase == "in":
                alpha = min(255, alpha + fade_speed)
                if alpha >= 255:
                    fade_phase = "hold"  # Stay visible
            elif fade_phase == "out":
                alpha = max(0, alpha - fade_speed)
                if alpha <= 0:
                    running = False
            
            # Update display
            fade_img.set_alpha(alpha)
            self.screen.fill("black")
            self.screen.blit(fade_img, (x_pos, y_pos))
            pg.display.update()
            clock.tick(60)

        self.state = States.PLAYTHROUGH

    def delay(self, event_list):
        # Set countdown starting number (for example, 3 seconds)
        countdown_number = 0.2
        while countdown_number > 0:
            self.draw() # Drawing all objects

            # Update the display
            pg.display.update()

            # Wait for a second before decreasing the countdown number
            time.sleep(0.1)

            # Decrease the countdown number
            countdown_number -= 0.1
    
        self.state = States.PLAYING

    def playing(self, event_list):
        
        # Controls in game:
        keys = pg.key.get_pressed()
        mouse_buttons = pg.mouse.get_pressed()
        mouse_pos = pg.mouse.get_pos()  # Mouse position
        
        # q for quit disabled
        # if keys[pg.K_q]:
        #     pg.quit()
        #     sys.exit()
        if keys[pg.K_ESCAPE]:
            print("ESCAPE PRESSED")
            self.state = States.PAUSE_MENU
            return
        
        # If the player controlled units list is empty we dont take inputs
        if self.units_player_controlled:
            if keys[pg.K_a]:
                self.units_player_controlled[0].rotate(-1.3)
            if keys[pg.K_d]:
                self.units_player_controlled[0].rotate(1.3)
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
            
            if not self.playthrough_started:
                if keys[pg.K_f]:
                    self.clear_all_map_data()
                    self.load_map()
                    self.load_map_textures()

        if self.fixed_delta_time:
            # Fixed timestep update for multiplayer
            self.fixed_delta_time_accumulator += self.delta_time
            
            while self.fixed_delta_time_accumulator >= self.delta_time:
                self.fixed_delta_time_accumulator -= self.delta_time
                self.update()
                self.multiplayer_run_playing()
                
                
            self.draw()
        else:     
            self.update()
            self.draw()
    
    def multiplayer_run_lobby(self):
        
        if self.hosting_game:
            all_player_names = [value["username"] for _, value in self.network.clients_meta.items()]  # Get all connected client names
            all_player_names.insert(0, "HOST BRIAN")    # Insert host name at index 0
            broadcast_data = str(all_player_names).encode()
            self.network.broadcast_data(b"CLNT" + broadcast_data)    # Send all names to clients
        
        if self.joined_game:
            
            all_player_names = self.network.client_list
            

        
        if all_player_names:
            if len(all_player_names) == 1:
                self.player1_button.change_button_text(str(all_player_names[0]))
            if len(all_player_names) == 2:
                self.player2_button.change_button_text(str(all_player_names[1]))
            if len(all_player_names) == 3:
                self.player3_button.change_button_text(str(all_player_names[2]))
    
    def multiplayer_run_playing(self):
        
        print(f"Host: {self.hosting_game} Client: {self.joined_game}")
        # Test that end player position
        if self.hosting_game and not self.joined_game:
            
            # Data transfer
            unit = self.units_player_controlled[0]
            
            pos = unit.pos
            rotation_body_angle = unit.degrees
            rotation_turret_angle = unit.turret_rotation_angle
            shot_fired = unit.shot_fired
            aim_pos = unit.aim_pos
            
            data = f"{str(pos[0])},{str(pos[1])},{str(rotation_body_angle)}, {str(rotation_turret_angle)}, {str(shot_fired)}, {str(aim_pos[0])}, {str(aim_pos[1])}"
            print(f"Sending test data: {data}")
            self.network.broadcast_data(b'STAT' + data.encode())
            
        if self.joined_game and not self.hosting_game:
            
            #print(f" Data from host {self.network.client_data_test}")
            pos, rotation_body_angle, rotation_turret_angle, shot_fired, aim_pos = self.network.client_data_test
            self.units_player_controlled[0].pos = pos
            self.units_player_controlled[0].degrees = rotation_body_angle
            self.units_player_controlled[0].turret_rotation_angle = rotation_turret_angle
            
        
            if int(shot_fired) == 1:
                #print(f"Trying to shoot with aimpos: {aim_pos}")
                self.units_player_controlled[0].shoot(aim_pos)




    def start_map(self):
        map_path = os.path.join(self.base_path_playthrough_maps, f"lvl{self.current_level_number}.txt")
        print(f"LOADING MAP: lvl{self.current_level_number}")
        self.load_map(map_path)
        self.load_map_textures()
    
    def clear_all_map_data(self):
        self.units_player_controlled.clear()
        self.units.clear()
        self.obstacles_sta.clear()
        self.obstacles_des.clear()
        self.obstacles_pit.clear()
        self.mines.clear()
        self.tracks.clear()


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
                        if len(self.units_player_controlled):
                            self.units_player_controlled[0].respawn() # The 0 indicates player tank
            
            # ----------------------------------------- ctrl-f (Test MED DETECT)-----------------------
            # if event.type == pg.MOUSEBUTTONUP:
            #     pos = pg.mouse.get_pos()
            #     if len(self.polygon_list_no_border):
            #         for poly in self.polygon_list_no_border:

            #             poly_pg_object = pg.draw.polygon(self.screen, (0,100,0), poly)
            #             if poly_pg_object.collidepoint(pos):
            #                 print("True mouse inside polygone")
            # ----------------------------------------- ctrl-f (Test MED DETECT)-----------------------
            
    # ============================================ Drawing/update ============================================     

    def update_delta_time(self):
        if not self.fixed_delta_time:
            # For singleplayer
            current_time = time.perf_counter()
            self.delta_time = min(current_time - self.last_frame_time, 0.1)
            self.last_frame_time = current_time
        else:
            # For multiplayer
            self.delta_time = self.fixed_delta_time_step

            
    def update(self):        
        
        # If playthrough has started
        if self.playthrough_started:
            
            # If all enemies die set player to godmode
            if all(unit.dead for unit in self.units if unit.team != self.units_player_controlled[0].team):
                self.units_player_controlled[0].godmode = True
                self.wait_time += self.delta_time
                
            # If player dead:
            if self.units_player_controlled[0].dead:
                self.wait_time += self.delta_time
            
            if self.wait_time >= self.wait_time_original:
                
                self.state = States.PLAYTHROUGH
                return 
        
        if self.time - self.last_print_time >= 0.5:
           
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
                    
                    random.choice(self.sound_effects["tracks"]).play()
    
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
            
        if self.show_ai_dodge:
            # SKAL SLETTES ELLER HAVDE EGEN SETTING KNAP (skal under sin egen dodge setting debug)
            if self.units[1].ai.proj_ray != None:
                for c1, c2 in self.units[1].ai.proj_ray:
                    pg.draw.line(self.screen, "red", c1, c2, 5) 
                    
            if unit.ai.behavior_state == "dodge":
                for node in unit.ai.dodge_nodes:
                    pg.draw.circle(self.screen, "red", node, 5)  # Draw nodes as circles
    
                        
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
        
        if self.frame == 0:
            self.frame = 0.000001
        
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
    SETTINGS_MAIN = "settings_main"
    SETTINGS_DEBUG = "settings_debug"
    SETTINGS_MULTIPLAYER = "settings_multiplayer"
    PAUSE_MENU = "pause_menu"
    PLAYTHROUGH = "playthrough"
    LEVEL_SELECT = "level_select"
    LOBBY_MENU = "lobby_menu"
    LOBBY_MENU_MAIN = "lobby_menu_main"
    PLAYING = "playing"
    COUNTDOWN = "countdown"
    DELAY = "delay"
    INFO_SCREEN = "infoscreen"
    END_SCREEN = "endscreen"
    CONTROL_SCREEN = "controlscreen"
    EXIT = "exit"
