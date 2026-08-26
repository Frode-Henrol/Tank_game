
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
        
        # self.dpi_fix()

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

        # Multiplayer snapshot broadcast is throttled well below the 100Hz sim rate - physics/AI
        # still run every tick, only how often the host tells clients about it is reduced (matters
        # for upload bandwidth over a real internet connection; loopback/LAN can trivially handle 100Hz).
        self.snapshot_broadcast_interval = 1/60
        self.snapshot_broadcast_accumulator = 0

        # Debug fps counter
        self.frame = 0
        self.total = 0
            
        self.last_frame_time = time.perf_counter()
            
        # Game objects
        self.units: list[Tank] = []
        self.units_dict = {}  # Maps tank IDs to unit objects
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
                
        # Loadout
        self.selected_loadout = "player_classic"  # Default
        
        # Game states:
        self.state = States.MENU

        # Multiplayer - initialized before the first load_map() below, which checks
        # hosting_game/joined_game to decide whether to inject extra player spawns.
        self.network = networking.Multiplayer()
        self.hosting_game = False
        self.joined_game = False
        self.username = f"Unknown{random.randint(0,1000)}"
        self.multiplayer_player_count = 1  # set for real in start_multiplayer_campaign() / from the host's level_result
        self.lobby_list_broadcast_interval = 1.0  # throttle for the host's "clients" name-list broadcast below
        self._last_lobby_list_broadcast_at = 0

        # Host: the latest level_result, periodically re-sent (see multiplayer_run_lobby()) so a
        # client that missed the original one-shot send (e.g. hadn't finished joining yet) still
        # catches up within about a second instead of waiting forever.
        self._level_result_seq = 0
        self._last_level_result_payload = None
        # Client: highest level_result seq already applied, so a repeat resend of one we've already
        # acted on is safely ignored instead of re-triggering a level reload mid-match.
        self._client_applied_level_result_seq = -1

        # Client-side render-only mirrors of the host's projectiles/mines, keyed by network id.
        # Never simulated locally (no .update()/.collision() calls) - purely driven by snapshots from the host.
        self._client_projectiles = {}
        self._client_mines = {}
        self._client_last_shot_counter = {}  # tank id -> last-seen shot_fired_counter, to edge-trigger cannon sound/muzzle flash

        self.load_gui()
        self.load_animations_and_misc()   
        self.load_sound_effects()     
          
        self.dead_enemies_before_death = set()
        self.load_map()    # A bit dumb but needed for test map feature in settings              
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
        self.directional_controls = False  # False = classic A/D rotate + W/S drive, True = WASD absolute-direction auto-rotate

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

        self.player_controlled_tank_num = 0
        self.m_key_prev = False
        self.r_key_prev = False


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

    def set_loadout(self, loadout_name: str):
        self.selected_loadout = loadout_name

    
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
            Button(left, 250, 300, 60, "Start game", States.LOADOUT_SELECT),
            Button(left, 350, 300, 60, "Level Select", States.LEVEL_SELECT),
            Button(left, 450, 300, 60, "Multiplayer (broken)", States.LOBBY_MENU),
            Button(left, 550, 300, 60, "Settings", States.SETTINGS_MAIN),
            Button(left, 650, 300, 60, "Quit game", States.EXIT)
        ]
        
        self.pause_menu_buttons = [
            Button(left, 250, 300, 60, "Resume", States.DELAY),
            Button(left, 350, 300, 60, "Settings", States.SETTINGS_MAIN),
            Button(left, 450, 300, 60, "Main menu", States.MENU, action=self.exit_to_main_menu)
        ]


        self.settings_buttons_main = [
            Button(left, 250, 300, 60, "Debug", States.SETTINGS_DEBUG),
            Button(left, 350, 300, 60, "Multiplayer", States.SETTINGS_MULTIPLAYER),
            Button(left, 450, 300, 60, "Controls", States.SETTINGS_CONTROLS),
            Button(left, 550, 300, 60, "Back", action=self.settings_back_button)
        ]
        
        self.settings_buttons_multiplayer = [
            Button(left, 250, 300, 60, "Stop socket", action=lambda: self.network.stop()),
            Button(left+400, 250, 300, 60, "send_join_request to server", action=lambda: self.network.send_join_request()),
            Button(left+400, 350, 300, 60, "send_input to server", action=lambda: self.network.send_input("DORIT".encode())),
            Button(left, 350, 300, 60, "Run mp method for test", action=lambda: self.multiplayer_run()),
            Button(left, 450, 300, 60, "Back", States.SETTINGS_MAIN)
        ]
    
        self.loadout_select_buttons = [
            Button(left, 175, 300, 60, "Select Loadout", color_disabled = "grey", disabled=True, text_color="black"),
            Button(left, 250, 300, 60, "Classic", States.CONTROL_SCREEN, action=lambda: self.set_loadout("player_classic")),
            Button(left, 350, 300, 60, "Sniper", States.CONTROL_SCREEN, action=lambda: self.set_loadout("player_sniper")),
            Button(left, 450, 300, 60, "Autocannon", States.CONTROL_SCREEN, action=lambda: self.set_loadout("player_autocannon")),
            Button(left, 550, 300, 60, "Bouncer", States.CONTROL_SCREEN, action=lambda: self.set_loadout("player_bouncer")),
            Button(left, 650, 300, 60, "Burst", States.CONTROL_SCREEN, action=lambda: self.set_loadout("player_burst")),
            Button(left, 800, 300, 60, "Main menu", States.MENU)
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

        self.settings_buttons_controls = [
            Button(left, 250, 300, 60, "Directional auto-rotate controls", hover_enabled=False, color_normal=(0,100,0), is_toggle_on=True, action=lambda: helper_functions.toggle_bool(self, "directional_controls")),
            Button(left, 450, 300, 60, "Back", States.SETTINGS_MAIN)
        ]
        # Custom fps choice field removed for now:
        # Textfield(left+350, 850, 300, 60, "100", on_mouse_leave_action=self.fps_button),
        
        self.level_selection_buttons = [
            Textfield(left, 250, 300, 60, "Level num"),
            Button(left, 350, 300, 60, "Play", States.LOADOUT_SELECT, action=self.lvl_select),
            Button(left, 450, 300, 60, "Back", States.MENU)  
        ]  
        
        self.lobby_menu_buttons = [
            Button(left, 175, 300, 60, "Host Game", color_disabled = "grey", disabled=True, text_color="black"),
            Textfield(left, 250, 300, 60, "Port (default 7777)"),
            Button(left, 325, 300, 60, "Start Host", States.LOBBY_MENU_MAIN, action=self.host_game_button),
            
            Button(left, 475, 300, 60, "Join Game", color_disabled = "grey", disabled=True, text_color="black"),
            Textfield(left, 550, 300, 60, "Host ip (LAN/public)"),
            Textfield(left, 625, 300, 60, "Port (default 7777)"),
            Button(left, 700, 300, 60, "Join Game", States.LOBBY_MENU_MAIN, action=self.join_game_button),
            
            Button(left, 850, 300, 60, "Back", States.MENU)  
        ]
        
        spacing_player = 75
        self.lobby_menu_main_buttons = [
            Button(left, 250, 300, 60, "Start Game", action=self.start_multiplayer_campaign),
            
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
        self.player_controlled_tank_num = 0  # Host always controls the first player slot on the multiplayer map

        port_field = self.lobby_menu_buttons[1]
        port_str = port_field.get_string()
        port = int(port_str) if port_str.isdigit() else networking.DEFAULT_PORT

        self.network.start_host(username=self.username, port=port)


    def join_game_button(self):
        self.joined_game = True

        host_ip_field = self.lobby_menu_buttons[4]
        port_field = self.lobby_menu_buttons[5]
        host_ip = "127.0.0.1" if host_ip_field.is_field_empty() else host_ip_field.get_string()
        port_str = port_field.get_string()
        port = int(port_str) if port_str.isdigit() else networking.DEFAULT_PORT

        self.network.start_client(username=self.username, host_ip=host_ip, port=port)

    def start_multiplayer_campaign(self):
        """Action for the lobby's "Start Game" button. Host-only - a client click is a no-op, since
        the client never decides this locally; it follows the host's level_result broadcast instead
        (see _broadcast_level_result/client_handle_level_result)."""
        if not self.hosting_game:
            return
        self.init_playthrough()
        self.playthrough_lives_original = self.playthrough_lives = 1  # one life per level, no retries
        # Host + everyone who's joined the lobby so far - fixed for the whole campaign (capped at 3,
        # matching the player1/2/3_tank blue/red/green assets).
        self.multiplayer_player_count = min(1 + len(self.network.clients_meta), 3)
        self.state = States.PLAYTHROUGH

    def shut_down_socket(self):
        self.hosting_game = False
        self.joined_game = False
        self.network.stop()
        self._client_projectiles.clear()
        self._client_mines.clear()
        self._client_last_shot_counter.clear()

        # Reset level_result session state so a stale cached payload from this session can't leak
        # into a fresh one (host side), and a fresh session's first "start" broadcast isn't wrongly
        # ignored as "already applied" due to a seq number left over from a previous session (client side).
        self._level_result_seq = 0
        self._last_level_result_payload = None
        self._client_applied_level_result_seq = -1

        # Return to the normal single-player default map
        self.clear_all_map_data()
        self.load_map()
        self.load_map_textures()

    def exit_to_main_menu(self):
        """Action for the pause menu's "Main menu" button. Tears down any active multiplayer session
        (socket, hosting_game/joined_game) before returning - otherwise the socket is left open and
        background threads keep running, and a later host attempt fails trying to rebind the same
        port (or a later join attempt talks over a stale, never-closed client socket)."""
        if self.hosting_game or self.joined_game:
            self.shut_down_socket()
            self.playthrough_started = False
            self.init_playthrough()

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
                  
    def inject_multiplayer_player_spawns(self, unit_list: list) -> list:
        """Multiplayer only: campaign maps only ever author one player spawn. Duplicate it up to
        self.multiplayer_player_count total player-controlled units (blue/red/green -
        player1_tank/player2_tank/player3_tank), all at the same position - existing tank-vs-tank
        repulsion physics separates them within the first couple of frames, and "same spot" is the
        only placement that's guaranteed not to land inside a wall on every level without
        hand-checking each map's local geometry. A solo host (player_count == 1) gets a no-op, so
        exactly one tank spawns, same as single-player."""
        PLAYER_TYPE_CODES = [0, 20, 21]  # tank_mappings: player1_tank (blue), player2_tank (red), player3_tank (green)
        player_count = min(self.multiplayer_player_count, len(PLAYER_TYPE_CODES))

        player_units = [u for u in unit_list if u[2] in PLAYER_TYPE_CODES]
        if not player_units or len(player_units) >= player_count:
            return unit_list  # nothing to duplicate from, or already enough spawns

        pos, angle, _unit_type, team = player_units[0]
        existing_codes = {u[2] for u in player_units}

        extra = []
        for code in PLAYER_TYPE_CODES:
            if len(player_units) + len(extra) >= player_count:
                break
            if code not in existing_codes:
                extra.append((pos, angle, code, team))

        return unit_list + extra

    def load_map(self, map_path: str =  os.path.join(MAP_DIR, r"map_test1.txt")) -> None:
        """Loads data from a map file"""
        
        # ==================== Load map  ====================
        # Map data i a tuple, where 1 entre is the polygon defining the map border the second is a list of all polygon cornerlists
        self.polygon_list, self.polygons_with_type, unit_list, self.node_spacing = helper_functions.load_map_data(map_path)

        if self.hosting_game or self.joined_game:
            unit_list = self.inject_multiplayer_player_spawns(unit_list)

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
        # Used for the textures and json. For players the "playerx_tank is for textures"
        # The json name for player loadouts are changed based on selected loadout
        # - this a bit of a lackluster solutions since i dont want to refactor the code
        tank_mappings = {0 : "player1_tank", 
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
                         19 : "zblack_tank",
                         20 : "player2_tank",    # Make player2 tank use same json as player1
                         21 : "player3_tank"     # Make player3 tank use same json as player1
                         
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
            if unit_type_json_format.startswith("player"):  # If a tank is a player used the selected loadout
                specific_unit_data = all_units_data_json[self.selected_loadout]
            else:
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
                                    ai_type            = ai_type,
                                    use_mag_reload_logic = specific_unit_data.get("use_mag_reload_logic", False),
                                    mag_size = specific_unit_data.get("mag_size", 5),
                                    reload_time = specific_unit_data.get("reload_time", 90)
                                    )
                
                # Init waypoint processing for tank
                unit_to_add.init_waypoint(self.grid_dict, self.border_polygon[3], self.node_spacing, self.valid_nodes)

                self.units_dict[unit_to_add.id] = unit_to_add  # Seperate dict to store tank with its id
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
            
            if self.state == States.PLAYING:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
            else:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
            
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
            elif self.state == States.SETTINGS_CONTROLS:
                self.settings_controls(event_list)
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
            elif self.state == States.LOADOUT_SELECT:
                self.loadout_select(event_list)
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

    def settings_controls(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.settings_buttons_controls, event_list, self.screen)
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
    
    def loadout_select(self, event_list):
        self.screen.fill("gray")
        self.handle_buttons(self.loadout_select_buttons, event_list, self.screen)
        pg.display.update()
    
    def playthrough(self, event_list):

        if self.playthrough_started == True:

            player_team = self.units_player_controlled[0].team

            # If gaining life
            if (self.current_level_number % self.new_life_interval == 0 and
                self.current_level_number not in self.levels_that_gave_life):
                self.added_life = True  # Bool for infoscreen
                self.playthrough_lives += 1
                self.levels_that_gave_life.add(self.current_level_number)  # Mark this level as having given a life
                print(f"ADDED life: {self.playthrough_lives - 1} -> {self.playthrough_lives}")

            # If everyone is dead (single-player: the one tank; multiplayer: every player tank)
            if all(p.dead for p in self.units_player_controlled):
                print("Reseting")

                # Store orderIDs of dead enemies before clearing
                current_dead_enemies = {
                unit.order_id for unit in self.units
                if unit.team != player_team and unit.dead
                }
                self.dead_enemies_before_death.update(current_dead_enemies)

                self.wait_time = 0
                self.playthrough_lives -= 1
                self.clear_all_map_data()
                self.start_map()
                self.state = States.INFO_SCREEN
                self.just_died = True
                print(f"Tank died life: {self.playthrough_lives} -> {self.playthrough_lives - 1}")
                self._broadcast_level_result("died")
                return

            # If level clear
            if all(unit.dead for unit in self.units if unit.team != player_team):
                self.dead_enemies_before_death = set()
                self.wait_time = 0
                self.current_level_number += 1
                self.clear_all_map_data()
                if self.current_level_number > self.last_level:
                    self.state = States.END_SCREEN
                    self._broadcast_level_result("victory")
                    return

                self.start_map()
                self.state = States.INFO_SCREEN
                print(f"Next level: {self.current_level_number-1} -> {self.current_level_number}")
                self._broadcast_level_result("level_complete")
                return

        # When playthrough done
        if self.playthrough_started == False:
            self.playthrough_started = True
            self.clear_all_map_data()
            self.start_map()
            self.state = States.INFO_SCREEN
            self._broadcast_level_result("start")
            return

    def _broadcast_level_result(self, outcome):
        """Host-only: tells clients a level/campaign transition just happened, since they never run
        this method themselves (host-authoritative win/lose decision) and would otherwise have no way
        to know to follow along into the same info/countdown/end screens with the same numbers.

        This is sent once here, but also cached and periodically re-sent from multiplayer_run_lobby()
        - a client that hasn't finished joining yet at this exact instant (a real, easy-to-hit race:
        nothing needs to be lost, "host clicks Start Game" just needs to land before "client finishes
        its JOIN handshake") would otherwise wait forever, since nothing else ever prompts it to leave
        the lobby. The seq number is what makes the resend safe - a client that already applied this
        result ignores repeats instead of being yanked back into INFO_SCREEN every second."""
        if not self.hosting_game:
            return
        self._level_result_seq += 1
        payload = {
            "type": "level_result",
            "seq": self._level_result_seq,
            "outcome": outcome,  # "start" | "died" | "level_complete" | "victory"
            "current_level_number": self.current_level_number,
            "playthrough_lives": self.playthrough_lives,
            "just_died": self.just_died,
            "added_life": self.added_life,
            "dead_enemies_before_death": list(self.dead_enemies_before_death),
            "player_count": self.multiplayer_player_count,
        }
        self._last_level_result_payload = payload
        self.network.host_to_clients_send(payload)
    
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
            if self.hosting_game or self.joined_game:
                self.shut_down_socket()  # also clears/reloads the default map and tears down networking
            else:
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

        if self.hosting_game or self.joined_game:
            self.shut_down_socket()  # also clears/reloads the default map and tears down networking
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

        # As a networked client we never simulate locally - input is only ever sent to the host,
        # never applied to our own tank objects (see client_send_input/client_apply_snapshot below).
        is_networked_client = self.joined_game and not self.hosting_game
        is_networked = self.hosting_game or self.joined_game

        # If the player controlled units list is empty we dont take inputs
        if not is_networked_client and self.units_player_controlled and self.units_player_controlled[0].dead != True:
            active_tank = self.units_player_controlled[self.player_controlled_tank_num]

            if self.directional_controls:
                dx = (1 if keys[pg.K_d] else 0) - (1 if keys[pg.K_a] else 0)
                dy = (1 if keys[pg.K_s] else 0) - (1 if keys[pg.K_w] else 0)
                if dx != 0 or dy != 0:
                    target_angle = helper_functions.find_angle(0, 0, dx, dy)
                    active_tank.rotate_towards(target_angle)
                    active_tank.move("forward")
            else:
                if keys[pg.K_a]:
                    active_tank.rotate(-1.3)
                if keys[pg.K_d]:
                    active_tank.rotate(1.3)
                if keys[pg.K_w]:
                    active_tank.move("forward")
                if keys[pg.K_s]:
                    active_tank.move("backward")

            active_tank.set_aim_target(mouse_pos)

            if mouse_buttons[0]:
                active_tank.shoot(mouse_pos)
            if keys[pg.K_SPACE]:
                active_tank.lay_mine()

            if not is_networked:
                m_key_current = keys[pg.K_m]
                if m_key_current and not self.m_key_prev:
                    self.switch_tank()
                self.m_key_prev = m_key_current

            r_key_current = keys[pg.K_r]
            if r_key_current and not self.r_key_prev:
                active_tank.reload()
            self.r_key_prev = r_key_current

            if not is_networked:
                if keys[pg.K_p]:
                    print(f"{self.show_pathfinding_paths=}")
                    # Only start a path search/init if the grid_dict is present
                    if self.grid_dict is not None:
                        active_tank.find_waypoint(mouse_pos)

                if keys[pg.K_o]:
                    active_tank.abort_waypoint()

                if not self.playthrough_started:
                    if keys[pg.K_f]:
                        self.clear_all_map_data()
                        self.load_map()
                        self.load_map_textures()

        def advance_one_tick():
            if is_networked_client:
                self.client_send_input(keys, mouse_buttons, mouse_pos)
                self.client_apply_snapshot()
                # client_handle_level_result() is NOT called here - see multiplayer_run_lobby(),
                # which calls it unconditionally every frame regardless of self.state. It has to be:
                # this method (playing()) only ever runs once self.state == States.PLAYING, but
                # client_handle_level_result() is what's supposed to *get* the client into that
                # state in the first place - calling it only from here is a circular dependency
                # that can never resolve (the client would sit in the lobby forever).
            else:
                if self.hosting_game:
                    self.host_apply_client_inputs()
                self.update()
                if self.hosting_game:
                    # Sim/AI/physics still run every tick above - only how often we tell clients
                    # about it is throttled, to keep upload bandwidth reasonable over the internet.
                    self.snapshot_broadcast_accumulator += self.delta_time
                    if self.snapshot_broadcast_accumulator >= self.snapshot_broadcast_interval:
                        self.snapshot_broadcast_accumulator -= self.snapshot_broadcast_interval
                        self.host_broadcast_snapshot()

        if self.fixed_delta_time:
            # Fixed timestep update for multiplayer
            self.fixed_delta_time_accumulator += self.delta_time

            while self.fixed_delta_time_accumulator >= self.delta_time:
                self.fixed_delta_time_accumulator -= self.delta_time
                advance_one_tick()
                if self.state != States.PLAYING:
                    # A level/campaign transition happened mid-loop (host's update()/playthrough(),
                    # or the client's client_handle_level_result()) - the map may have just been torn
                    # down and rebuilt, so stop feeding it more ticks from this call.
                    break

            self.draw()
        else:
            advance_one_tick()
            self.draw()
    
    def switch_tank(self):
        self.player_controlled_tank_num += 1
        if self.player_controlled_tank_num >= len(self.units_player_controlled):
            self.player_controlled_tank_num = 0
        
        
    # ========================= MULTIPLAYER =================================
    def multiplayer_run_lobby(self):

        # [DIAG] once/sec proof that the main loop is actually reaching this function repeatedly -
        # if this print stops appearing (or never appears more than once), the main loop itself is
        # stalled/blocked somewhere, independent of anything network-related.
        now_diag = time.time()
        if now_diag - getattr(self, "_last_diag_heartbeat_at", 0) >= 1.0:
            self._last_diag_heartbeat_at = now_diag
            print(f"[DIAG] multiplayer_run_lobby alive at {now_diag:.2f} "
                  f"hosting_game={self.hosting_game} joined_game={self.joined_game} "
                  f"client_id={self.network.client_id} state={self.state}")

        if self.hosting_game:
            if not self.playthrough_started:
                # Lobby-only: drop clients who've gone silent (crashed/closed/lost connection) so
                # their name stops showing in the player list. Not done mid-game - see
                # prune_stale_clients()'s docstring for why that's handled differently there.
                self.network.prune_stale_clients()

            # list(...) snapshots clients_meta before iterating - it's written from the network
            # thread (a new JOIN) and read here from the main thread; iterating the live dict
            # directly can raise "dictionary changed size during iteration" if a join lands mid-loop.
            # Building this list is cheap (no network I/O) and done every frame so the host's own
            # on-screen player list stays instantly responsive - only the actual send below is throttled.
            all_player_names = [value["username"] for _, value in list(self.network.clients_meta.items())]  # Get all connected client names
            all_player_names.insert(0, "HOST BRIAN")    # Insert host name at index 0

            # multiplayer_run_lobby() is called every iteration of the main loop, unthrottled (up to
            # ~100/sec), for as long as hosting_game is true - including during actual gameplay.
            # Sending this over the network doesn't need to be anywhere near that frequent; throttle
            # it to once a second like the join retry/heartbeat cadence, rather than blasting every
            # connected client with a packet every frame forever just to show a name list.
            now = time.time()
            if now - self._last_lobby_list_broadcast_at >= self.lobby_list_broadcast_interval:
                self._last_lobby_list_broadcast_at = now
                self.network.host_to_clients_send({"type": "clients", "names": all_player_names})    # Send all names to clients

                # Re-send the latest campaign-state message on the same cadence. The one-shot send
                # in _broadcast_level_result() can be missed by a client that hasn't finished
                # joining yet at that exact instant; this guarantees it (or a late joiner) catches
                # up within about a second instead of waiting forever. Safe to repeat indefinitely -
                # client_handle_level_result() ignores anything it's already applied via the seq number.
                if self._last_level_result_payload is not None:
                    self.network.host_to_clients_send(self._last_level_result_payload)

        if self.joined_game:
            self.network.retry_join_if_needed()
            self.network.send_lobby_heartbeat()

            # Called here (not from playing()) specifically because multiplayer_run_lobby() runs
            # every frame regardless of self.state - including while still in the lobby, which is
            # exactly when this needs to run to ever get the client OUT of the lobby. It's a no-op
            # whenever there's nothing pending (self.network.level_result is None).
            self.client_handle_level_result()

            if self.network.client_id == 0:
                # Still handshaking (or it failed) - show that instead of a blank/stale player list.
                # connection_status_text() re-checks client_id itself, and that field is updated by
                # the background recv thread - it can flip to nonzero in the gap between our check
                # above and the call below, making the function return None right at the exact
                # moment we successfully connect. Button.draw() can't render None, so fall back to a
                # plain string rather than crash the render loop on a race that only exists for one frame.
                self.player1_button.change_button_text(self.network.connection_status_text() or "Connecting...")
                all_player_names = []
            else:
                all_player_names = self.network.client_list

                # Set the controlled tank to client id: player 1: id: 2, player 2: id: 2 etc
                self.player_controlled_tank_num = self.network.client_id    # Minus 1 to get correct player_controlled index

        if all_player_names:
            if len(all_player_names) == 1:
                self.player1_button.change_button_text(str(all_player_names[0]))
            if len(all_player_names) == 2:
                self.player2_button.change_button_text(str(all_player_names[1]))
            if len(all_player_names) == 3:
                self.player3_button.change_button_text(str(all_player_names[2]))

    # ---- Host: applies each connected client's latest input to their proxy tank, before self.update() ----
    def host_apply_client_inputs(self):
        for addr, inp in list(self.network.input_from_clients.items()):
            tank = self.units_dict.get(inp.get("tank_id"))
            if tank is None:
                continue

            if inp.get("directional"):
                dx = (1 if inp.get("rotate_right") else 0) - (1 if inp.get("rotate_left") else 0)
                dy = (1 if inp.get("move_back") else 0) - (1 if inp.get("move_fwd") else 0)
                if dx != 0 or dy != 0:
                    target_angle = helper_functions.find_angle(0, 0, dx, dy)
                    tank.rotate_towards(target_angle)
                    tank.move("forward")
            else:
                if inp.get("rotate_left"):
                    tank.rotate(-1.3)
                if inp.get("rotate_right"):
                    tank.rotate(1.3)
                if inp.get("move_fwd"):
                    tank.move("forward")
                if inp.get("move_back"):
                    tank.move("backward")

            aim = (inp.get("aim_x", 0), inp.get("aim_y", 0))
            tank.set_aim_target(aim)

            if inp.get("fire"):
                tank.shoot(aim)
            if inp.get("mine"):
                tank.lay_mine()
            if inp.get("reload"):
                tank.reload()

    # ---- Host: broadcasts the authoritative world state to all clients, after self.update() ----
    def host_broadcast_snapshot(self):
        # Map stale (mid-game disconnected) client ids to the tank id they control, per the
        # established client_id -> units_player_controlled[client_id] convention.
        disconnected_tank_ids = set()
        for cid in self.network.stale_client_ids():
            if 0 <= cid < len(self.units_player_controlled):
                disconnected_tank_ids.add(self.units_player_controlled[cid].id)

        # Also set directly on the host's own live Tank objects, so the host's own screen shows the
        # same indicator (draw() reads this uniformly; the host never goes through client_apply_snapshot()).
        for unit in self.units:
            unit.net_disconnected = unit.id in disconnected_tank_ids

        tanks = [
            {
                "id": unit.id,
                "x": unit.pos[0], "y": unit.pos[1],
                "degrees": unit.degrees,
                "turret": unit.turret_rotation_angle,
                "dead": unit.dead,
                "shot_counter": unit.shot_fired_counter,
                "disconnected": unit.id in disconnected_tank_ids,
            }
            for unit in self.units
        ]

        projectiles = [
            {
                "uid": proj.uid,
                "x": proj.pos[0], "y": proj.pos[1],
                "dir_x": proj.direction[0], "dir_y": proj.direction[1],
                "bounce_count": proj.bounce_count,
            }
            for proj in self.projectiles
        ]

        mines = [
            {
                "id": mine.id,
                "x": mine.pos[0], "y": mine.pos[1],
                "explode_radius": mine.explode_radius,
                "team": mine.team,
                "exploded": mine.is_exploded,
            }
            for mine in self.mines
        ]

        self.network.host_to_clients_send({
            "type": "snapshot",
            "tanks": tanks,
            "projectiles": projectiles,
            "mines": mines,
            "obstacles_des_alive": [obstacle.id for obstacle in self.obstacles_des],
        })

    # ---- Client: sends this tick's local input to the host. The client never simulates locally - no
    # prediction in v1, so nothing here mutates any Tank; it's a pure network send. ----
    def client_send_input(self, keys, mouse_buttons, mouse_pos):
        if not (self.units_player_controlled and 0 <= self.player_controlled_tank_num < len(self.units_player_controlled)):
            return

        tank = self.units_player_controlled[self.player_controlled_tank_num]

        self.network.client_to_host_send({
            "type": "input",
            "tank_id": tank.id,
            "directional": self.directional_controls,
            "move_fwd": bool(keys[pg.K_w]),
            "move_back": bool(keys[pg.K_s]),
            "rotate_left": bool(keys[pg.K_a]),
            "rotate_right": bool(keys[pg.K_d]),
            "aim_x": mouse_pos[0],
            "aim_y": mouse_pos[1],
            "fire": bool(mouse_buttons[0]),
            "mine": bool(keys[pg.K_SPACE]),
            "reload": bool(keys[pg.K_r]),
        })

    # ---- Client: applies the latest snapshot from the host directly to local objects for rendering.
    # Replaces self.update() entirely on the client - no local AI/physics/collision runs here. ----
    def client_apply_snapshot(self):
        snapshot = self.network.snapshot_from_host
        if snapshot is None:
            return

        # Tanks
        for tank_data in snapshot.get("tanks", []):
            unit = self.units_dict.get(tank_data["id"])
            if unit is None:
                continue

            unit.pos = [tank_data["x"], tank_data["y"]]
            unit.degrees = tank_data["degrees"]
            unit.turret_rotation_angle = tank_data["turret"]
            unit.net_disconnected = tank_data.get("disconnected", False)

            dead = tank_data["dead"]
            if dead != unit.dead:
                unit.make_dead(dead)
            unit.time_of_death = unit.time_of_death + 1 if unit.dead else 0

            shot_counter = tank_data["shot_counter"]
            if shot_counter > self._client_last_shot_counter.get(tank_data["id"], -1):
                self._client_last_shot_counter[tank_data["id"]] = shot_counter
                random.choice(unit.cannon_sounds).play()
                unit.muzzle_flash_animation = Animation(images=unit.animations["muzzle_flash"], frame_delay=2, delta_time=self.delta_time)
                barrel_length = 50
                rad_angle = np.radians(unit.turret_rotation_angle)
                barrel_end = (unit.pos[0] + barrel_length * np.cos(rad_angle), unit.pos[1] + barrel_length * np.sin(rad_angle))
                unit.muzzle_flash_animation.start(pos=barrel_end, angle=unit.turret_rotation_angle + 90)

        # Projectiles: render-only mirrors, keyed by network id, one tick of alive=False before removal
        # (mirrors the single tick a real dead projectile spends in self.projectiles on the host,
        # which is what makes draw()'s "if not proj.alive: handle_projectile_explosion(proj)" fire once).
        current_ids = {p["uid"] for p in snapshot.get("projectiles", [])}

        for uid in list(self._client_projectiles.keys()):
            if not self._client_projectiles[uid].alive:
                del self._client_projectiles[uid]

        for proj_data in snapshot.get("projectiles", []):
            uid = proj_data["uid"]
            proj = self._client_projectiles.get(uid)
            if proj is None:
                proj = Projectile(unit_pos=(proj_data["x"], proj_data["y"]),
                                   startpos=(proj_data["x"], proj_data["y"]),
                                   direction=(proj_data["dir_x"], proj_data["dir_y"]),
                                   speed=0, bounce_limit=999999, id=-1)
                proj.init_sound_effects(self.sound_effects)
                self._client_projectiles[uid] = proj

            prev_bounce_count = proj.bounce_count
            proj.pos = [proj_data["x"], proj_data["y"]]
            proj.direction = (proj_data["dir_x"], proj_data["dir_y"])
            proj.bounce_count = proj_data["bounce_count"]
            if proj.bounce_count > prev_bounce_count:
                random.choice(proj.hit_sounds).play()

        for uid, proj in self._client_projectiles.items():
            if uid not in current_ids:
                proj.alive = False

        self.projectiles = list(self._client_projectiles.values())

        # Mines: render-only mirrors, keyed by network id
        current_mine_ids = {m["id"] for m in snapshot.get("mines", [])}

        for mine_data in snapshot.get("mines", []):
            uid = mine_data["id"]
            mine = self._client_mines.get(uid)
            if mine is None:
                mine = Mine(image=None, spawn_point=(mine_data["x"], mine_data["y"]),
                            explode_radius=mine_data["explode_radius"], owner_id=-1, team=mine_data["team"])
                self._client_mines[uid] = mine

            was_exploded = mine.is_exploded
            mine.pos = (mine_data["x"], mine_data["y"])
            mine.is_exploded = mine_data["exploded"]
            if mine.is_exploded and not was_exploded:
                self.handle_mine_explosion(mine)

        for uid in list(self._client_mines.keys()):
            if uid not in current_mine_ids:
                del self._client_mines[uid]

        self.mines = list(self._client_mines.values())

        # Destructible obstacles
        alive_ids = set(snapshot.get("obstacles_des_alive", []))
        if {o.id for o in self.obstacles_des} != alive_ids:
            self.obstacles_des = [o for o in self.obstacles_des if o.id in alive_ids]
            self.des_texture_surface = self.wrap_texture_on_polygon_type(self.obstacles_des, self.images_des)

    # ---- Client: mirrors a host campaign transition (level clear / full wipe / victory / initial
    # start) locally - reloads the same map the host just loaded, copies over the level/lives
    # bookkeeping, then transitions into the same info/countdown/end screens single-player already
    # uses, unmodified. The client never decides any of this itself - see _broadcast_level_result. ----
    def client_handle_level_result(self):
        result = self.network.level_result
        if result is None:
            return
        self.network.level_result = None  # one-shot event, not a continuously-latest field - consume it

        if result["seq"] <= self._client_applied_level_result_seq:
            # Already applied this one - just the host's periodic resend catching up to us (it
            # can't tell whether we got the original send, so it keeps re-sending regardless).
            # Ignore it rather than re-reloading the level / re-entering INFO_SCREEN mid-match.
            return
        self._client_applied_level_result_seq = result["seq"]

        self.current_level_number = result["current_level_number"]
        self.playthrough_lives = result["playthrough_lives"]
        self.just_died = result["just_died"]
        self.added_life = result["added_life"]
        self.dead_enemies_before_death = set(result["dead_enemies_before_death"])
        self.multiplayer_player_count = result["player_count"]

        if result["outcome"] == "victory":
            self.state = States.END_SCREEN
            return

        self.clear_all_map_data()
        self.start_map()
        self.state = States.INFO_SCREEN

    # =======================================================================


    def start_map(self):
        map_path = os.path.join(self.base_path_playthrough_maps, f"lvl{self.current_level_number}.txt")
        print(f"LOADING MAP: lvl{self.current_level_number}")
        self.load_map(map_path)
        self.load_map_textures()
    
    def clear_all_map_data(self):
        self.units_player_controlled.clear()
        self.units.clear()
        self.units_dict.clear()
        self.obstacles_sta.clear()
        self.obstacles_des.clear()
        self.obstacles_pit.clear()
        self.mines.clear()
        self.tracks.clear()
        self.projectiles.clear()

        # Reset id counters so a fresh map load always produces the same deterministic ids,
        # regardless of how many tanks/obstacles were loaded earlier this process. Multiplayer
        # relies on host and client assigning identical ids to identical map units.
        Tank._id_counter = 0
        Obstacle._id_counter = 0


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

            player_team = self.units_player_controlled[0].team

            # If all enemies die set every player tank to godmode
            if all(unit.dead for unit in self.units if unit.team != player_team):
                for p in self.units_player_controlled:
                    p.godmode = True
                self.wait_time += self.delta_time

            # If every player tank is dead (single-player: the one tank; multiplayer: all of them):
            if all(p.dead for p in self.units_player_controlled):
                self.wait_time += self.delta_time

                # Set all enemy units to godmod to prevent killing after the last player dies
                for unit in self.units:
                    unit.godmode = True

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

            # mov_avg_fps = sum(self.fps_list) / len(self.fps_list)
            # mov_delta_fps = sum(self.delta_time_list) / len(self.delta_time_list)
        
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
                
                if unit.dead == False:
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

        # Multiplayer: disconnect indicators
        if self.hosting_game or self.joined_game:
            for unit in self.units:
                if getattr(unit, "net_disconnected", False) and not unit.dead:
                    label_font = pg.font.Font(None, 24)
                    label = label_font.render("DISCONNECTED", True, (255, 60, 60))
                    label_rect = label.get_rect(center=(unit.pos[0], unit.pos[1] - 40))
                    self.screen.blit(label, label_rect)

            if self.joined_game and self.network.host_connection_lost():
                banner_font = pg.font.Font(None, 64)
                banner = banner_font.render("Lost connection to host", True, (255, 60, 60))
                banner_rect = banner.get_rect(center=(self.WINDOW_W // 2, 80))
                self.screen.blit(banner, banner_rect)

        self.draw_ammo_ui()

        if self.show_debug_info:
            self.render_debug_info()
            
        # self.render_debug_info()
            
        pg.display.update()
        if self.cap_fps:
            self.clock.tick(self.fps)   # Controls FPS
        else:
            self.clock.tick()   # Uncapped Controls FPS
    
    def draw_ammo_ui(self):
        """Draw ammo ui over tank if reload logic is turned on"""
        if not self.units_player_controlled:
            return
        
        player = self.units_player_controlled[self.player_controlled_tank_num]
        if not player.use_magazine or player.dead:
            return
        
        mag_size = player.mag_size
        shots_left = mag_size - player.shots_fired_in_mag
        reloading = player.reloading if hasattr(player, "reloading") else False  # fallback if not present
        
        # Position: 40px above tank
        x, y = player.pos
        bar_width = 60
        bar_height = 8
        gap = 2
        segment_width = bar_width // mag_size
        
        for i in range(mag_size):
            rect = pg.Rect(x - bar_width // 2 + i * (bar_width // mag_size + gap), y - 50, bar_width // mag_size, bar_height)
            color = (200, 0, 0) if i >= shots_left else (0, 200, 0)
            pg.draw.rect(self.screen, color, rect)
            pg.draw.rect(self.screen, (0, 0, 0), rect, 1)  # border

        # Flashing grey if reloading
        flash_on = (pg.time.get_ticks() // 250) % 2 == 0
        flash_color = (180, 180, 180) if flash_on else (60, 60, 60)

        for i in range(mag_size):
            color = flash_color if reloading else (0, 200, 0) if i < shots_left else (200, 0, 0)
            rect = pg.Rect(x - bar_width // 2 + i * (segment_width + gap), y - 50, segment_width, bar_height)
            pg.draw.rect(self.screen, color, rect)
            pg.draw.rect(self.screen, (0, 0, 0), rect, 1)


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
    SETTINGS_CONTROLS = "settings_controls"
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
    LOADOUT_SELECT = "loadout_select"
    EXIT = "exit"
