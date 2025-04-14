import pygame as pg
import utils.deflect as df
from object_classes.projectile import Projectile
from object_classes.obstacle import Obstacle
from object_classes.mine import Mine
import utils.helper_functions as helper_functions
import numpy as np
import random
import pathfinding
from scipy.spatial import KDTree
import heapq

class Tank:
    _id_counter = 0 
    
    def __init__(self, 
                 startpos: tuple,
                 speed: float,
                 firerate: float,
                 speed_projectile: float,
                 spawn_degress: int,
                 bounch_limit: int, 
                 mine_limit: int,
                 global_mine_list: list[Mine],
                 projectile_limit: int,
                 images, 
                 death_image,
                 use_turret,
                 team,
                 ai_type = None,
                 godmode = False,
                 draw_hitbox = True):
        
        self.pos = list(startpos)
        self.direction = (0,0)  # Skal rettes
        self.degrees = spawn_degress
        self.speed = speed  # Used to control speed so it wont be fps bound
        self.speed_original = speed
        
        self.is_moving = False  # True if moving: 1 = forward, -1 = backward
        self.is_moving_dir = 0
        self.is_moving_false_time_start = 5
        self.is_moving_false_time = 0
        
        # Team
        self.team = team
        
        # Projectile
        self.speed_projectile = speed_projectile # Scale the tanks projectile speed
        self.bounch_limit = bounch_limit
        
        # Mines
        self.mine_limit = mine_limit
        self.mine_cooldown_amount = 60 
        self.mine_cooldown = 0
        self.global_mine_list = global_mine_list
        self.unit_mine_list = []

        self.current_speed = [0,0]
        self.firerate = firerate
        self.cannon_cooldown = 0
        self.projectile_limit = projectile_limit
        
        # Slowdown effect when shooting
        self.shot_slowness_cooldown_amount = 0
        # self.shot_slowness_cooldown_amount = 6  # Duration in frames of the slowdown
        self.shot_slowness_cooldown = 0
        self.slowdown_amount = 0.1      # Procentage of the original speed to keep when slowed
        
        # Hitbox
        self.init_hitbox(spawn_degress)    # Init the hitbox in the correct orientation
        self.draw_hitbox = draw_hitbox
            
        # Health
        self.dead = False
        
        # Ekstra features
        self.godmode = godmode     # Toggle godmode for all tanks
        
        # Tank images:
        self.image = images[0]
        self.death_image = death_image
        self.active_image = images[0]
        
        # Turret image:
        self.turret_image = images[1]
        
        # Projectiles from current tank
        self.projectiles: list[Projectile] = []
        
        # Use turret?
        self.use_turret = use_turret
        self.turret_rotation_angle = 0
        
        # Pathfinding and waypoint logic
        self.go_to_waypoint = False     # Bool to control if tanks should follow waypoint queue
        self.waypoint_queue = []    # Tank starts with empty waypoint queue

        # Tank id
        self.id = Tank._id_counter
        Tank._id_counter += 1  # increment for next tank
        
        # AI
        # TEST DIC
        self.ai_type = ai_type  
        self.pos_dir = (0,0)
        
        self.units = []

        
    def init_ai(self, obstacles: list[Obstacle], projectiles: list[Projectile], mines: list[Mine], all_ai_data_json: dict):
        self.ai = TankAI(self, None, self.valid_nodes, self.units.copy(), obstacles, projectiles, mines, config=all_ai_data_json) if self.ai_type != "player" else None
    
    def init_sound_effects(self, sound_effects):
        self.sound_effects = sound_effects
        
        self.cannon_sounds = sound_effects[:4]
        self.death_sounds = sound_effects[4:8]

    
    def set_units(self, units):
        self.units = units
    
    def init_hitbox(self, spawn_degress):
        x = self.pos[0]
        y = self.pos[1]
        size_factor = 20
        # top left, top right, bottom right, bottom left ->  Front, right, back, right (line orientation in respect to tank, when run through coord_to_coordlist function)
        self.hitbox = [(x-size_factor, y-size_factor),
                       (x+size_factor, y-size_factor),
                       (x+size_factor, y+size_factor),
                       (x-size_factor, y+size_factor)]
        
        self.rotate_hit_box(spawn_degress)
        
    def move(self, direction: str):
        if self.dead and not self.godmode:
            return
            
        if direction == "forward":
            dir = 1
        elif direction == "backward":
            dir = -1
        
        self.is_moving_false_time = self.is_moving_false_time_start
        self.is_moving_dir = dir
        self.is_moving = True
            
        # Move tank image
        self.pos[0] = self.pos[0] + dir * self.direction[0] * self.speed
        self.pos[1] = self.pos[1] + dir * self.direction[1] * self.speed
        
        # Move hit box:
        for i in range(len(self.hitbox)):
            x, y = self.hitbox[i]  # Unpack the point
            
            moved_x = x + dir * self.direction[0] * self.speed
            moved_y = y + dir * self.direction[1] * self.speed
            self.hitbox[i] = (moved_x, moved_y)
    
    def respawn(self):
        self.make_dead(False)
            
    def draw(self, surface):
        
        # TEMP: constant to make sure tank image points the right way
        tank_correct_orient = -90
        rotated_tank = pg.transform.rotate(self.active_image, -self.degrees + tank_correct_orient)
        tank_rect = rotated_tank.get_rect(center=self.pos)
        surface.blit(rotated_tank, tank_rect.topleft)

        if self.dead:
            return
        # Turret Rotation Logic
        if self.ai == None:
            # Control of turret when player controlled
            target_coord = pg.mouse.get_pos()
            self.turret_rotation_angle = helper_functions.find_angle(self.pos[0], self.pos[1], target_coord[0], target_coord[1])
            
        # Control shooting slowness effect
        if self.shot_slowness_cooldown > 0:
            self.shot_slowness_cooldown -= 1
            self.speed = self.speed_original * self.slowdown_amount  # Slowdown amount
        else: 
            self.speed = self.speed_original
        
        # Rotate turret image independently
        rotated_turret = pg.transform.rotate(self.turret_image, -1 * self.turret_rotation_angle - 90)

        # Get turret rect centered at new turret position
        turret_rect = rotated_turret.get_rect(center=self.pos)

        # Draw turret
        surface.blit(rotated_turret, turret_rect.topleft)
        
        # ============================= Other logic ================================
        # Decrease cooldown each new draw
        if self.cannon_cooldown > 0:
            self.cannon_cooldown -= 1
        
        if self.mine_cooldown > 0:
            self.mine_cooldown -= 1
        
        # Remove dead projectiles
        self.projectiles[:] = [p for p in self.projectiles if p.alive]
        
        #AI
        if self.ai and not self.dead:
            self.ai.update()
            
        # Pathfinding / waypoint logic if it is activated
        if self.go_to_waypoint:
            self.move_to_node(self.current_node)
            
        if self.is_moving_false_time > 0:
            self.is_moving_false_time -= 1
        
        if self.is_moving_false_time == 0: 
            self.is_moving = False
            
    def rotate(self, deg: int):
        if self.dead and not self.godmode:
            return
        
        # Scale rotation to match speed
        deg *= self.speed
        
        # Rotate tank image
        self.degrees += deg
        rads = np.radians(self.degrees)
        
        # Update direction vector
        self.direction = np.cos(rads), np.sin(rads)
        
        # When rotating we also rate the tank hitbox
        self.rotate_hit_box(deg)
           
    def rotate_hit_box(self, deg):
        # Rotate tank hitbox
        rads = np.radians(deg)  # The hitbox is rotated specified degress
        
        # Rotate all 4 corners in the hitbox
        for i in range(len(self.hitbox)):
            x, y = self.hitbox[i]
            
            # Corrected 2D rotation formulawa
            rotated_x = self.pos[0] + (x - self.pos[0]) * np.cos(rads) - (y - self.pos[1]) * np.sin(rads)
            rotated_y = self.pos[1] + (x - self.pos[0]) * np.sin(rads) + (y - self.pos[1]) * np.cos(rads)

            # Update the list in place
            self.hitbox[i] = (rotated_x, rotated_y)
            
    def collision(self, line: tuple, collision_type: str) -> bool:
        """line should be a tuple of 2 coords"""
        
        # Coords of the "surface" line in the polygon
        line_coord1, line_coord2 = line
        
        # Find coord where tank and line meet. Try all 4 side of tank
        hit_box_lines = helper_functions.coord_to_coordlist(self.hitbox)
        
        # Check each line in hitbox if it itersect a line: surface/projectile/etc
        for i in range(len(hit_box_lines)):
            start_point, end_point = hit_box_lines[i]
            intersect_coord = df.line_intersection(line_coord1, line_coord2, start_point, end_point)
        
            # Only execute code when a collision is present. The code under will push the tank back with the normal vector to the line "surface" hit (with same magnitude as unit direction vector)
            if intersect_coord != None:
                print(f"Tank hit line at coord: ({float(intersect_coord[0]):.1f},  {float(intersect_coord[1]):.1f})")
                
                # If collision is a ____
                if collision_type == "surface":
                    # Find normal vector of line
                    normal_vector1, normal_vector2 = df.find_normal_vectors(line_coord1, line_coord2)
                    # - We only use normalvector2 since all the left sides of the hitbox lines point outwards
                    
                    # Calculate magnitude scalar of units direction vector
                    magnitude_dir_vec = helper_functions.get_vector_magnitude(self.direction) 
                    
                    # Scale the normal vector with the previous magnitude scalar
                    normal_scaled_x, normal_scaled_y = normal_vector2[0] * magnitude_dir_vec, normal_vector2[1] * magnitude_dir_vec
                    
                    # Update unit postion
                    self.pos = [self.pos[0] + normal_scaled_x * self.speed, self.pos[1] + normal_scaled_y * self.speed]
                    
                    # Update each corner position in hitbox
                    for i in range(len(self.hitbox)):
                        x, y = self.hitbox[i]
                        self.hitbox[i] = (x + normal_scaled_x * self.speed, y + normal_scaled_y * self.speed)
                        
                        
                elif collision_type == "projectile":
                    self.make_dead(True)
                    return True
                else:
                    print("Hitbox collision: type is unknown")
        
    def make_dead(self, active):
        
        
        if active and not self.godmode:
            print("Tank dead")
            self.dead = True
            self.active_image = self.death_image
            random.choice(self.death_sounds).play()
        else:
            self.dead = False
            self.active_image = self.image
            
               
    def shoot(self, aim_pos: tuple | None):
        # Dont shoot if dead, reach projectile limit or cooldown hasnt been reached
        if self.dead and not self.godmode:
            return
        if len(self.projectiles) >= self.projectile_limit:
            return
        if self.cannon_cooldown != 0:
            return
        
        self.cannon_cooldown = self.firerate * 5
        # At the moment the distance is hard coded, IT must be bigger than hit box or tank will shot itself.
        spawn_distance_from_middle = 30
        
        self.shot_slowness_cooldown = self.shot_slowness_cooldown_amount
        
        if self.use_turret:
            if self.ai == None:
                # Find the unit vector between mouse and tank. This is the projectile unit direction vector
                unit_direction = helper_functions.unit_vector(self.pos, aim_pos)
            else:
                # If ai controlled we use the turret angle as the projectile path
                aim_x = np.cos(np.radians(self.turret_rotation_angle))
                aim_y = np.sin(np.radians(self.turret_rotation_angle))
                
                aim_pos = aim_x + self.pos[0], aim_y + self.pos[1]
                print(f"Angle: {self.turret_rotation_angle:.2f} Aim: {aim_pos[0]:.2f},{aim_pos[1]:.2f}")
                unit_direction = helper_functions.unit_vector(self.pos, aim_pos)
                
            projectile_direction = unit_direction
            
                
        # Find position for spawn of projectile
        spawn_projectile_pos = [self.pos[0] + unit_direction[0]*spawn_distance_from_middle, self.pos[1] + unit_direction[1]*spawn_distance_from_middle]

        projectile = Projectile(spawn_projectile_pos, projectile_direction, speed=self.speed_projectile, bounce_limit=self.bounch_limit)
        projectile.init_sound_effects(self.sound_effects)
        self.projectiles.append(projectile)
        
        # Play sound when firing
        random.choice(self.cannon_sounds).play()
                                                                      
        print(self.direction)
        

    def lay_mine(self):
        
        # Remove exploded mines
        temp_mine = []
        for mine in self.unit_mine_list:
            if not mine.is_exploded:
                temp_mine.append(mine)
        self.unit_mine_list = temp_mine
        
        if self.mine_cooldown == 0 and len(self.unit_mine_list) < self.mine_limit:
            mine = Mine(spawn_point=self.pos, explode_radius=100, owner_id=self.id, team=self.team)
            
            self.mine_cooldown = self.mine_cooldown_amount
            
            self.unit_mine_list.append(mine)
            self.global_mine_list.append(mine)

    def apply_repulsion(self, other_unit, push_strength=1.0):
        """Pushes colliding tanks in correct direction"""
        
        # Vector from other_unit to this tank
        dx = self.pos[0] - other_unit.pos[0]
        dy = self.pos[1] - other_unit.pos[1]
        dist_sq = dx ** 2 + dy ** 2

        if dist_sq == 0:
            return  # Avoid division by zero

        dist = dist_sq ** 0.5
        repulsion_vector = (dx / dist * push_strength, dy / dist * push_strength)

        # Move this tank slightly away
        self.pos[0] += repulsion_vector[0]
        self.pos[1] += repulsion_vector[1]

        # Also move hitbox accordingly
        for i in range(len(self.hitbox)):
            x, y = self.hitbox[i]
            self.hitbox[i] = (x + repulsion_vector[0], y + repulsion_vector[1])

    def __str__(self):
        return f"Pos: {self.pos} ai: {self.ai_type}"

    def get_projectile_list(self):
        return self.projectiles
    
    def get_pos(self):
        return self.pos

    def get_hitbox_corner_pairs(self):
        return helper_functions.coord_to_coordlist(self.hitbox)
    
    def get_hitbox_front_pair(self):
        return self.hitbox[0], self.hitbox[1]
    
    def get_ai(self):
        print(f"AI type: {self.ai_type}")
        return self.ai_type
        
    def get_death_status(self):
        return self.dead

    def get_direction_vector(self):
        return self.direction
    
    def get_waypoint_queue(self):
        return self.waypoint_queue
    
    def toggle_godmode(self):
        self.godmode = not self.godmode
        
    def toggle_draw_hitbox(self):
        self.draw_hitbox = not self.draw_hitbox

    # ---------- Pathfinding ----------
    def init_waypoint(self, grid_dict: dict, top_left: tuple, node_spacing: int, valid_nodes: list[tuple]):
        # Functions makes sure to set up tank for at given path for pathfinding
        self.node_spacing = node_spacing
        self.top_left = top_left
        self.grid_dict = grid_dict
        self.valid_nodes = valid_nodes
    
    def find_waypoint(self, destination_coord: tuple) -> None:
        """Starts a waypoint action. Unit will pathfind to the destination coordinate"""
        # Get path to the node
        path = self.find_path(destination_coord)
        
        if path is None:
            print("Could not find path")
            return
        
        # Save the path as the waypoint queue  (reversing since .pop() is used in move_to_node)
        self.waypoint_queue = [pathfinding.grid_to_pygame(x, self.top_left, self.node_spacing) for x in path]
        self.waypoint_queue.reverse()
        
        # Active bool that allows tank to follow waypoint
        self.go_to_waypoint = True
        
        # Set current node:
        self.next_node()
        
    def find_path(self, destination_coord: tuple[int,int]) -> list[tuple[int,int]]:
        """Finds the path from the tank to a destination coordinate"""
        # Converts tank position to a node position in the node grid
        tank_pos_grid = pathfinding.pygame_to_grid(self.pos, self.top_left, self.node_spacing)
        destination_coord_grid = pathfinding.pygame_to_grid(destination_coord, self.top_left, self.node_spacing)
        
        # Find path
        return pathfinding.find_path(self.grid_dict, tank_pos_grid, destination_coord_grid)
    
    def move_to_node(self, node_coord: tuple[int, int]):
        """Controls the tank's movement toward the next node in the waypoint."""

        # ---------- Vector to Target ----------
        to_target = (node_coord[0] - self.pos[0], node_coord[1] - self.pos[1])
        to_target_mag = np.hypot(to_target[0], to_target[1])

        if to_target_mag == 0:
            return  # Already at the target

        to_target_unit = (to_target[0] / to_target_mag, to_target[1] / to_target_mag)

        # ---------- Forward or Reverse Logic ----------
        # Determine if it's shorter to reverse
        dot_forward = self.direction[0] * to_target_unit[0] + self.direction[1] * to_target_unit[1]
        dot_forward = np.clip(dot_forward, -1.0, 1.0)

        angle_diff_deg = np.degrees(np.arccos(dot_forward))

        if angle_diff_deg > 90:
            use_reverse = True
            effective_direction = (-self.direction[0], -self.direction[1])
        else:
            use_reverse = False
            effective_direction = self.direction

        # ---------- Recalculate with Effective Direction ----------
        dot = effective_direction[0] * to_target_unit[0] + effective_direction[1] * to_target_unit[1]
        dot = np.clip(dot, -1.0, 1.0)
        angle_diff_deg = np.degrees(np.arccos(dot))

        # ---------- Distance & Rotation ----------
        distance_to_node = to_target_mag
        pos_dir = (self.pos[0] + effective_direction[0], self.pos[1] + effective_direction[1])

        TURN_THRESHOLD_MIN = 5      # Degrees before we skip rotating
        TURN_THRESHOLD_MAX = 45     # Degrees above which we rotate without moving
        DISTANCE_THRESHOLD = 50     # Distance in pixels before node is considered reached

        # Rotation speed scaling
        rotate_amount = 5
        max_rotation_speed = 15
        min_rotation_speed = 0.01
        rotation_speed = min(max_rotation_speed, rotate_amount * (angle_diff_deg / 90))
        rotation_speed = max(rotation_speed, min_rotation_speed)

        if distance_to_node > DISTANCE_THRESHOLD:
            # Rotate if needed
            if angle_diff_deg > TURN_THRESHOLD_MIN:
                if helper_functions.left_turn(self.pos, pos_dir, node_coord):
                    self.rotate(rotation_speed)
                else:
                    self.rotate(-rotation_speed)

            # Move only if we're reasonably aligned
            if angle_diff_deg < TURN_THRESHOLD_MAX:
                if use_reverse:
                    self.move("backward")
                else:
                    self.move("forward")
        else:
            # Move to next node or end
            if self.waypoint_queue:
                self.next_node()
                print("Node finished.")
            else:
                print("Waypoint queue finished")
                self.go_to_waypoint = False


    def next_node(self):
        # Gets the next node in the waypoint queue and removes it and stores it in seperate variable
        self.current_node = self.waypoint_queue.pop()

    def abort_waypoint(self):
        """Abort a way point in action"""
        self.waypoint_queue.clear()
        self.go_to_waypoint = False
        
    def convert_node_to_grid(self, coord: tuple[float, float]) -> tuple[int, int]:
        coord = pathfinding.pygame_to_grid(coord, self.top_left, self.node_spacing)
        return pathfinding.grid_to_pygame(coord, self.top_left, self.node_spacing)
        

class TankAI:
    def __init__(self, 
                 tank: Tank, 
                 personality, 
                 valid_nodes: list[tuple], 
                 units: list[Tank], 
                 obstacles: list[Obstacle], 
                 projectiles: list[Projectile],
                 mines: list[Mine],
                 config: dict):
        
        # Generel tank information
        self.tank = tank                # The tank instance this AI controls
        self.spawn_coord = tank.pos     # Save the spawn coordinate
        self.personality = personality  # UNUSED
        
        # Pathfinding nodes
        self.valid_nodes_original = valid_nodes.copy()
        self.valid_nodes = np.array(valid_nodes)  
        self.kd_tree = KDTree(self.valid_nodes)  
        self.possible_nodes = []
        
        # Import all data from map
        self.units = units              # All units
        self.units.remove(self.tank)    # Remove itself from the units list
        self.obstacles = obstacles      # All obstacles
        self.projectiles = projectiles  # All projectiles
        self.mines = mines              # All mines
        
        # Tank that is under targeting
        self.targeted_unit = None
        
        # Controls how often we do a update
        self.frame_counter = 0
        
        # Starting state
        self.behavior_state = BehaviorStates.IDLE
        
        # No speed means tank will stay in idle state
        self.movement = self.tank.speed != 0
        
        # Tank that is under targeting
        self.targeted_unit = self.units[0] if self.units else None              # TEST using player as hardcoded target
        self.unit_target_line = None                    # Init line between target and tank
        self.unit_target_line_color = (255, 182, 193) 
        self.target_in_sight = False
        
        self.dist_to_target_direct = 9999
        self.dist_to_target_path = 9999
        
        # Patrol
        self.patrol_radius = config.get("patrol_radius", 200)
        self.dist_leave_patrol = config.get("dist_leave_patrol", 500)
        
        # Defend
        self.dist_leave_defend = config.get("dist_leave_defend", 800)
        
        # Attack
        self.dist_leave_attack = config.get("dist_leave_attack", 200)
        
        # Dodge
        self.can_dodge_proj = config.get("can_dodge_proj", True)
        self.can_dodge_mine = config.get("can_dodge_mine", True)
        self.dist_start_dodge = config.get("dist_start_dodge", 45)
        self.dodge_cooldown_val = config.get("dodge_cooldown_val", 30)
        
        self.dodge_cooldown = 0      
        self.dodge_nodes = []
        self.closest_projectile = (None, 9999)
        
        # Shooting
        self.angle_diff_deg = 9999 # The current angle between target and turret
        
        self.rotation_speed = config.get("rotation_speed", 1)     # Degress pr frame
        
        self.aiming_angle = config.get("aiming_angle", 25)      # The angle which the turret will wander off from target. 
        self.rotation_mult_max = config.get("rotation_mult_max", 2)  # Maxium rotation multiplier when angledifference is 180 degress
        self.rotation_mult_min = config.get("rotation_mult_min", 0.8)    # Minimum rotation multiplier when angledifference is 0 degress
        
        self.perfect_aim = config.get("perfect_aim", False)       # Removes random turret wandering
        self.turret_turn_threshold = 2  # Under this angle from target the turret stop moving
        
        self.advanced_targeting = config.get("advanced_targeting", True)  # Advanced targeting (True: line of fire check. False: Only distance check)
        self.predictive_targeting = config.get("predictive_targeting", True) # Try to lead the shots for units
        self.predictive_targeting_chance = config.get("predictive_targeting_chance", 50) # 0 - 100%    
        
        self.shoot_threshold = config.get("shoot_threshold", 10)   # Smaller value means more precise shots are taken.  
        self.safe_threshold = config.get("safe_threshold", 50)     # Increase value to prevent hitting itself.  
        
        self.shoot_enemy_projectiles = config.get("shoot_enemy_projectiles", True)
        self.shoot_enemy_projectiles_range = config.get("shoot_enemy_projectiles_range", 100)   # The perpendicular distance to project path
        
        # Salvo
        self.salvo_cooldown_amount = config.get("salvo_cooldown_amount", 120) 
        self.salvo_cooldown = 0
        
        # Wander
        self.wander_radius = config.get("wander_radius", 200)
        self.defend_time = config.get("defend_time", 600)
        self.timer = 0
        
        # Misc
        self.current_target_angle = None  # Store the randomized target angle
        self.can_shoot = False
        
        # Mine
        self.mine_chance = config.get("mine_chance", 10000)
        self.closest_mine = (None, 0)

        # Ray predict data
        self.update_rate = 1
        self.max_bounces = self.tank.bounch_limit - 1 # Temp remove one since 1 is added for projectile logic to work properly
        self.ray_path = [((0,0),(0,0)),((0,0),(0,0))]
    

    def update(self):
        self.frame_counter += 1
        self.targeting()
        
        self.misc_updates()
        
        if self.movement == False:
            return
        
        if self.behavior_state == BehaviorStates.DODGE:
            self.handle_dodge_state()
            return
        
        # Avoid projectiles
        if self.can_dodge_proj and self.closest_projectile[1] < self.dist_start_dodge and self.dodge_cooldown == 0:
            self.behavior_state = BehaviorStates.DODGE
            self.dodge()
            self.dodge_cooldown = self.dodge_cooldown_val  # e.g. 30 frames cooldown
            return
        
        # Avoid mines
        if self.can_dodge_mine and self.mines and self.closest_mine != None and self.dodge_cooldown == 0:
            if self.closest_mine[1] < self.closest_mine[0].explode_radius:
                self.avoid_mine()
                self.dodge_cooldown = self.dodge_cooldown_val # e.g. 30 frames cooldown
    
        if self.behavior_state == BehaviorStates.IDLE:
            self.idle()
        elif self.behavior_state == BehaviorStates.PATROLLING:
            self.patrol()
        elif self.behavior_state == BehaviorStates.DEFENDING:
            self.defend()
        elif self.behavior_state == BehaviorStates.ATTACKING:
            self.attack()
        elif self.behavior_state == BehaviorStates.WANDER:
            self.wander()
            
    # ======================= Behavior states =======================
    def idle(self):
        
        
        
        if self.movement:
            self.behavior_state = BehaviorStates.PATROLLING
            self.targeting_state = TargetingStates.TARGETING
        
        # Stays in idle if tank has no movement
        # When no movement the targeting state is searching
    
    def patrol(self):
        if self.tank.go_to_waypoint == False:
            self.find_path_within_coord(self.spawn_coord, self.patrol_radius)
            self.behavior_state == BehaviorStates.IDLE
            return
        
        # Leave patrol mode if target to close
        if self.target_in_sight or self.dist_to_target_path < self.dist_leave_patrol:
            self.behavior_state = BehaviorStates.DEFENDING
            return
         
    def defend(self):
        self.closest_projectile = (None, 9999)
        
        if self.timer == 0:
            self.timer = self.defend_time 

        if self.timer > 0:
            self.timer -= 1
            
        if self.timer == 1:
            print("ATTACK")
            self.tank.abort_waypoint()
            self.behavior_state = BehaviorStates.ATTACKING
            return
            
        # Leave defend mode if target to far away
        if self.dist_to_target_direct > self.dist_leave_defend:
            self.tank.abort_waypoint()
            self.behavior_state = BehaviorStates.ATTACKING
            return
        
        
        self.min_dist_node = 300
        self.max_dist_node = self.min_dist_node + 400
        self.keep_distance_behavior()
        
    def attack(self):
        # Leave attack mode if target close
        if self.advanced_targeting:
            if self.target_in_sight or self.dist_to_target_direct < 100:
                self.tank.abort_waypoint()
                self.behavior_state = BehaviorStates.DEFENDING
                return
        else:
            if self.dist_to_target_direct < self.dist_leave_attack:
                self.tank.abort_waypoint()
                self.behavior_state = BehaviorStates.DEFENDING
                return

        
        print(self.targeted_unit.pos)
        if self.tank.go_to_waypoint == False:
            self.find_path_within_coord(self.targeted_unit.pos, 100)
            return
               
    def wander(self):

        self.find_path_within_coord(self.tank.pos, self.wander_radius)

        if self.timer == 0:
            rand = random.randint(0,100)
            
            if rand > 90:
                self.tank.abort_waypoint()
                self.behavior_state = BehaviorStates.DEFENDING
            else:
                self.tank.abort_waypoint()
                self.behavior_state = BehaviorStates.ATTACKING
            self.timer = 180

    def dodge(self):
        
        # Peform checks that will prevent from doing the dodge
        if not self.projectiles:
            self.behavior_state = BehaviorStates.DEFENDING
            return

        if self.tank.go_to_waypoint == False:
            self.behavior_state = BehaviorStates.DEFENDING
            return
        
        if self.closest_projectile[1] > self.dist_start_dodge:
            self.behavior_state = BehaviorStates.DEFENDING
            return

        self.tank.abort_waypoint() 
        projectile = self.closest_projectile[0]
        vx, vy = projectile.direction

        # Get both perpendicular dodge directions (left and right)
        dodge_dirs = [(-vy, vx), (vy, -vx)]

        dodge_nodes_pot = set()
        # Find left and right point (vinkelret) from the closest projectil path
        for dodge_dir in dodge_dirs:
            norm = np.linalg.norm(dodge_dir)
            if norm == 0:
                continue
            dodge_dir = (dodge_dir[0] / norm, dodge_dir[1] / norm)

            for i in range(50, 150, 50):
                target = (
                    self.tank.pos[0] + dodge_dir[0] * i,
                    self.tank.pos[1] + dodge_dir[1] * i
                )
                target = self.tank.convert_node_to_grid(target)     # Convert coords to pathfinding nodes
                dodge_nodes_pot.add(target)

        # Make sure only to use nodes that are valid on the map
        dodge_nodes_valid = list(dodge_nodes_pot & set(self.valid_nodes_original))
        
        # Exit if no valid move
        if not dodge_nodes_valid:
            return
        
        dodge_nodes_valid_dist = []
        for node in dodge_nodes_valid:
            dist = helper_functions.distance(node, self.closest_projectile[0].pos)
            dodge_nodes_valid_dist.append((node, dist))
        
        target_node = max(dodge_nodes_valid_dist, key=lambda x: x[1])[0]
        self.dodge_nodes = [target_node]

        self.tank.find_waypoint(target_node)
        
    def handle_dodge_state(self):
        
        # If not projectiles exit dodge
        if self.closest_projectile[1] > self.dist_start_dodge:
            self.behavior_state = BehaviorStates.DEFENDING
            return

        # If not projectiles exit dodge
        if self.tank.go_to_waypoint == False:
            self.behavior_state = BehaviorStates.DEFENDING
            return
    # ======================= Targeting states =======================
        
    def targeting(self):
        
        # Predictive targeting projectiles
        # Check for the projectiles with closest distance not radial but path intersect with tank pos
        if (self.shoot_enemy_projectiles == True and self.closest_projectile[0] != None and self.closest_projectile[1] < self.shoot_enemy_projectiles_range):
            target_pos = self.closest_projectile[0].pos
        else:
            # Predictive targeting unit
            chance = random.randint(0,100)
            if self.predictive_targeting and self.targeted_unit.is_moving and chance < self.predictive_targeting_chance:
                target_pos = self.intercept_point(target_object=self.targeted_unit)
            else:
                target_pos = self.targeted_unit.pos
        
        self.debug_target_pos = target_pos          
        
        # Move turret
        self.move_turret_to_target(target_pos, self.aiming_angle)
        
        # If salvo cooldown has not been reached the unit wont shot
        if self.salvo_cooldown > 0:
            return
        
        if self.frame_counter % self.update_rate == 0:
            self.ray_path = self.deflect_ray()
                
        self.can_shoot = True
        
        # First pass check for friendly fire and self harm
        for line_segment in self.ray_path:
            start, end = line_segment
            
            # 1. Dont shoot mines that are close enough to kill the unit
            for mine in self.mines:
                if (helper_functions.distance(mine.pos, self.tank.pos) < mine.explode_radius
                    and self.is_point_within_segment_and_threshold(start, end, mine.pos, self.safe_threshold)):
                    self.can_shoot = False
                    return
            
            # 2. Check self-collision first 
            if self.can_shoot and self.is_point_within_segment_and_threshold(start, end, self.tank.pos, self.safe_threshold):
                self.can_shoot = False
                return
                
            # 3. Check for ally collisions (all units except target)
            for unit in self.units:
                if unit != self.targeted_unit and not unit.dead:
                    if self.is_point_within_segment_and_threshold(start, end, unit.pos, self.safe_threshold):
                        self.can_shoot = False
                        return
            
        # Second pass check if valid target is in range
        for line_segment in self.ray_path:
            start, end = line_segment
            # 3. Only shot target if it's safe to shoot
            if self.can_shoot:
                if self.is_point_within_segment_and_threshold(start, end, target_pos, self.shoot_threshold):
                    self.tank.shoot(None)
                    return

    # ======================= Target filtering =====================
    def is_point_within_segment_and_threshold(self, segment_start, segment_end, point, threshold):
        """Check if point is between segment points and within shoot threshold"""
        if not self.is_point_between_segment(segment_start, segment_end, point):
            return False
            
        dist = helper_functions.point_to_line_distance(segment_start, segment_end, point)
        return dist < threshold

    def is_point_between_segment(self, segment_start, segment_end, point):
        """Check if point lies between the start and end points of a segment"""
        # Vector from segment start to end
        segment_vec = (segment_end[0] - segment_start[0], segment_end[1] - segment_start[1])
        
        # Vector from segment start to point
        point_vec = (point[0] - segment_start[0], point[1] - segment_start[1])
        
        # Dot product to check if point is in segment's "forward" direction
        dot_product = (segment_vec[0] * point_vec[0] + segment_vec[1] * point_vec[1])
        
        # If dot product is negative, point is behind segment start
        if dot_product < 0:
            return False
        
        # Check if point is within segment length
        segment_length_sq = (segment_vec[0]**2 + segment_vec[1]**2)
        point_length_sq = (point_vec[0]**2 + point_vec[1]**2)
        
        # If point is further than segment length, it's beyond the segment
        if point_length_sq > segment_length_sq:
            return False
        
        return True
        
    # ======================= Misc functions =======================
    
    def misc_updates(self):
        self.unit_target_line = self.tank.pos, self.targeted_unit.pos
        
        # Direct distance updated every 10 frames
        if self.frame_counter % 10 == 0:
            self.dist_to_target_direct = helper_functions.distance(self.tank.pos, self.targeted_unit.pos)
  
        # Path distance updated every 60 frames
        if self.frame_counter % 60 == 0:
            try:
                self.dist_to_target_path = len(self.tank.find_path(self.targeted_unit.pos)) * self.tank.node_spacing 
            except:
                print("Tank blocked in")
            self.hit_scan_check_proximity()  
        
        if self.timer > 0:
            self.timer -= 1  
        
        self.find_closest_projectile()
        self.find_closest_mine()
            
        if self.dodge_cooldown > 0:
            self.dodge_cooldown -= 1
            
        # Mine laying
        if self.tank.mine_limit > 0 and self.behavior_state == BehaviorStates.ATTACKING:
            randint = random.randint(0, self.mine_chance)
            if randint == 1:
                if self.mines:
                    for mine in self.mines:
                        if helper_functions.distance(mine.pos, self.tank.pos) > mine.explode_radius*1.5:
                            self.tank.lay_mine()
                else:
                    self.tank.lay_mine()
        
        # Cooldown after salvo
        if len(self.tank.projectiles) == self.tank.projectile_limit:
            self.salvo_cooldown = self.salvo_cooldown_amount
        
        if self.salvo_cooldown > 0:
            self.salvo_cooldown -= 1
        
        # BLOT TEST:
        if not self.target_in_sight:
            self.unit_target_line_color = (255, 182, 193)
        else:
            self.unit_target_line_color = (144, 238, 144)
        
    def find_path_within_coord(self, patrol_coord: tuple, patrol_radius: int):     
        if self.tank.go_to_waypoint:
            return  # If already moving, do nothing

        # Build a KD-tree for fast nearest-neighbor search
        kd_tree = KDTree(self.valid_nodes)
        
        # Query KD-tree for nodes within min_dist and max_dist from target
        nearby_indices = kd_tree.query_ball_point(patrol_coord, patrol_radius)
        
        # Choose random node
        random_indice = random.choice(nearby_indices)
        chosen_node = self.valid_nodes[random_indice]
        
        # Find a path to the node
        self.tank.find_waypoint(chosen_node)
    
    def move_turret_to_target(self, target_coord: tuple[float, float], angle_inaccuracy: float):
        # Calculate target direction vector
        target_direction_vector = (target_coord[0] - self.tank.pos[0], 
                                target_coord[1] - self.tank.pos[1])
        
        # Convert turret rotation angle to a direction vector
        rads = np.radians(self.tank.turret_rotation_angle)
        turret_direction = (np.cos(rads), np.sin(rads)) 
        
        # Compute the perfect target angle (without inaccuracy)
        perfect_target_angle = np.degrees(np.arctan2(target_direction_vector[1], target_direction_vector[0]))

        if self.perfect_aim:
            self.current_target_angle = perfect_target_angle  # No random inaccuracy
        else:
            # If we don't have a randomized target angle or it's reached, generate a new one
            if self.current_target_angle is None or abs(self.angle_diff_deg) < self.turret_turn_threshold:
                inaccuracy_offset = random.uniform(-angle_inaccuracy, angle_inaccuracy)  # Random offset in range [-angle_inaccuracy, +angle_inaccuracy]
                self.current_target_angle = perfect_target_angle + inaccuracy_offset  # New randomized target angle

        # Compute new direction vector for the selected target angle
        target_rads = np.radians(self.current_target_angle)
        target_vector = (np.cos(target_rads), np.sin(target_rads))

        # Compute angle difference between the turret and the selected target
        self.angle_diff_deg = helper_functions.vector_angle_difference(target_vector, turret_direction)

        # Maps angle diff to a multiplier, meaning higher angle diff gives faster rotation speed
        rotation_multiplier = helper_functions.map_x_to_y(self.angle_diff_deg, 0, 180, self.rotation_mult_min, self.rotation_mult_max)

        # Rotate turret toward the target angle
        if self.angle_diff_deg > self.turret_turn_threshold:
            if helper_functions.left_turn((0,0), turret_direction, target_vector):
                self.tank.turret_rotation_angle += self.rotation_speed * rotation_multiplier
            else:
                self.tank.turret_rotation_angle -= self.rotation_speed * rotation_multiplier
        
        # Debug visualization
        self.debug_turret_v = (
            self.tank.pos, 
            (turret_direction[0] * 100 + self.tank.pos[0], turret_direction[1] * 100 + self.tank.pos[1])
        )
        
        self.turret_direction = turret_direction 
        
    def keep_distance_behavior(self):
        """Move to a location that keeps the tank within the min and max distance from the player.
        If the player moves too far away, approach them."""
        if self.tank.go_to_waypoint:
            return  # If already moving, do nothing

        # Build a KD-tree for fast nearest-neighbor search
        kd_tree = KDTree(self.valid_nodes)
        
        # Query KD-tree for nodes within min_dist and max_dist from target
        target_pos = self.targeted_unit.pos
        nearby_indices = kd_tree.query_ball_point(target_pos, self.max_dist_node)
        
        possible_nodes = []
        for idx in nearby_indices:
            node = self.valid_nodes[idx]
            dist_node_target = helper_functions.distance(node, target_pos)
            dist_node_unit = helper_functions.distance(node, self.tank.pos)

            if self.min_dist_node < dist_node_target < self.max_dist_node:
                possible_nodes.append((node, dist_node_target, dist_node_unit))

        # If there are valid choices, move to the best one. The node that is closest to the tanks current position
        # This prevents the tank chosing node behind the enemy.
        amount_nodes = 20  # How many nodes should be randomly chosen
        possible_nodes = heapq.nsmallest(amount_nodes, possible_nodes, key=lambda x: x[2])

        if possible_nodes:
            chosen_node = random.choice(possible_nodes)
            self.tank.find_waypoint(chosen_node[0])
        
        self.possible_nodes = [x[0] for x in possible_nodes]

    def find_closest_mine(self):
        if not self.mines:
            self.closest_mine = None
            return
            
        mines_data = []
        for mine in self.mines:
            mine_dist = helper_functions.distance(self.tank.pos, mine.pos)
            mines_data.append((mine, mine_dist))
        
        self.closest_mine = min(mines_data, key=lambda x: x[1])

    def avoid_mine(self):
        # Return if unit is not within mine explosion distance.
        # Also create list of all mines and there distance to unit
        
        # Update valid nodes to exclude dangerous nodes
        temp_nodes = []
        for node in self.valid_nodes:
            for mine in self.mines:
                if helper_functions.distance(node, mine.pos) > mine.explode_radius:
                    temp_nodes.append(node)
        valid_nodes = np.array(temp_nodes)

        # Build a KD-tree for fast nearest-neighbor search
        kd_tree = KDTree(valid_nodes)
        
        # Query KD-tree for nodes within min_dist and max_dist from target
        self.mine_avoid_max_dist = 400  # Could be moved to init if it should be different per unit
        target_pos = self.closest_mine[0].pos
        nearby_indices = kd_tree.query_ball_point(target_pos, self.mine_avoid_max_dist)
        
        possible_nodes = []
        for idx in nearby_indices:
            node = valid_nodes[idx]
            dist_node_target = helper_functions.distance(node, target_pos)
            dist_node_unit = helper_functions.distance(node, self.tank.pos)
            
            # Remove nodes within explosion distance + 50 in safety margin
            if self.closest_mine[0].explode_radius + 50 < dist_node_target < self.mine_avoid_max_dist:
                possible_nodes.append((node, dist_node_target, dist_node_unit))

        # If there are valid choices, move to the best one. The node that is closest to the tanks current position
        # This prevents the tank chosing node behind the enemy.
        amount_nodes = 20  # How many nodes should be randomly chosen (permanent 1?)
        possible_nodes = heapq.nsmallest(amount_nodes, possible_nodes, key=lambda x: x[2])

        if possible_nodes:
            chosen_node = random.choice(possible_nodes)
            print(f"Tank: {self.tank.id} is avoiding mine, finding path")
            self.tank.find_waypoint(chosen_node[0])
        
        self.possible_nodes = [x[0] for x in possible_nodes]
        
    def hit_scan_check_proximity(self):
        # Check for intersections with obstacles
        coord1, coord2 = self.unit_target_line 
        
        for obstacle in self.obstacles:
            for corner_pair in obstacle.get_corner_pairs():
                result = df.line_intersection(map(float,coord1), map(float,coord2), corner_pair[0], corner_pair[1])
                #print(f"Checking intersection: {corner_pair} and {coord1, coord2} -> Result: {result}")
                if result != None:
                    self.target_in_sight = False
                    return False
                
        # Get turret's direction as a unit vector
        turret_direction_x = np.cos(np.radians(self.tank.turret_rotation_angle))
        turret_direction_y = np.sin(np.radians(self.tank.turret_rotation_angle))

        # Define a maximum distance for the hit scan (how far you want to check in front of the turret)
        max_hit_scan_distance = 100  # This can be adjusted based on your game needs
        
        # Calculate the end point of the hit scan line in front of the turret
        coord1 = self.tank.pos  # Starting point is the tank's position
        coord2 = (self.tank.pos[0] + turret_direction_x * max_hit_scan_distance, 
                self.tank.pos[1] + turret_direction_y * max_hit_scan_distance)  # End point is a fixed distance in turret's direction
        
        
        # Check for intersections with other units
        for unit in self.units:
            if unit.ai is None:  # Skip units without AI
                continue

            # Skip dead units
            if unit.dead:
                continue
            
            # Calculate minimum distance from the line to the unit (using the unit's position)
            min_dist = helper_functions.point_to_line_distance(coord1, coord2, unit.pos)
            tank_width = 45  # Width of the tank (may need to adjust for your game)
            
            if min_dist < tank_width:
                self.target_in_sight = False
                return False
        
        # If no obstacles or units block the path
        self.target_in_sight = True
        return True
        
    def find_closest_projectile(self):
        closest = None
        min_dist = float("inf")

        for proj in self.projectiles:
            # Calculate the direction of the projectile
            direction_vector = np.array(proj.pos) - np.array(proj.startpos)  # From start to current position
            to_tank_vector = np.array(self.tank.pos) - np.array(proj.pos)     # From projectile to tank

            # Compute the dot product to check if the projectile is moving towards the tank
            dot_product = np.dot(direction_vector, to_tank_vector)

            if dot_product > 0:  # Positive dot product means projectile is moving towards the tank
                # Calculate the distance from the projectile's path to the tank
                dist = helper_functions.point_to_line_distance(proj.startpos, proj.pos, self.tank.pos)

                if dist < min_dist:
                    min_dist = dist
                    closest = proj

        if closest:
            self.closest_projectile = (closest, min_dist)
        else:
            self.closest_projectile = (None, 9999)

    def deflect_ray(self):        
        lines = []
        direction = self.turret_direction
        offset_start = 30
        
        current_point = (self.tank.pos[0] + direction[0] * offset_start, 
                         self.tank.pos[1] + direction[1] * offset_start)
        bounce_count = 0
        max_distance = 2000
        
        while bounce_count <= self.max_bounces:
            # Calculate end point of this ray segment
            end_point = (
                current_point[0] + direction[0] * max_distance,
                current_point[1] + direction[1] * max_distance
            )
            
            closest_intersection = None
            closest_distance = float('inf')
            closest_normal = None
            
            # Find closest intersection with any obstacle
            for obstacle in self.obstacles:
                for corner_pair in obstacle.get_corner_pairs():
                    intersect = df.line_intersection(corner_pair[0], corner_pair[1], current_point, end_point)
                    
                    if intersect:
                        # Calculate distance and ensure we don't pick the same point
                        dist = helper_functions.distance(current_point, intersect)
                        if dist < closest_distance and dist > 1:  # Small threshold to avoid self-intersection
                            closest_distance = dist
                            closest_intersection = intersect
                            # Get both possible normals using your function
                            normal1, normal2 = df.find_normal_vectors(corner_pair[0], corner_pair[1])
                            # Choose the normal facing the incoming ray using dot product
                            dot1 = normal1[0]*direction[0] + normal1[1]*direction[1]
                            closest_normal = normal1 if dot1 < 0 else normal2
            
            # If no intersection found, draw the remaining ray and exit
            if not closest_intersection:
                lines.append((tuple(current_point), tuple(end_point)))
                break
                
            # Add this segment to the path (ensure tuples for consistency)
            lines.append((tuple(current_point), tuple(closest_intersection)))
            
            # Calculate new direction using your deflection function
            if closest_normal:
                direction = df.find_deflect_vector(closest_normal, direction)
                # Move the start point slightly away from the intersection to prevent self-collision
                current_point = (
                    closest_intersection[0] + direction[0] * 0.1,
                    closest_intersection[1] + direction[1] * 0.1
                )
            else:
                current_point = closest_intersection
                
            bounce_count += 1
        
        return lines
            
    def intercept_point(self, target_object, projectile = False):
        """Finds predictive coord for the unit and some target (other unit or projectile)"""
        # Calculate relative vector from shooter to target
        rel_vec = (
            target_object.pos[0] - self.tank.pos[0],
            target_object.pos[1] - self.tank.pos[1]
        )

        # Target's movement speed
        target_speed = target_object.speed

        # Projectile speed
        proj_speed = self.tank.speed_projectile

        if not projectile:
            # Direction modifier: 1 = forward, -1 = reverse
            dir = target_object.is_moving_dir
        else:
            dir = 1

        # Movement direction vector (multiplied by direction modifier)
        d = (
            target_object.direction[0] * dir,
            target_object.direction[1] * dir
        )

        # Convert to NumPy array and normalize to unit vector
        d = np.array(d)
        d = d / np.linalg.norm(d)

        # Coefficients for the quadratic equation: A*t² + B*t + C = 0
        A = target_speed**2 - proj_speed**2
        B = 2 * target_speed * np.dot(rel_vec, d)
        C = np.dot(rel_vec, rel_vec)

        # Discriminant of the quadratic
        discriminant = B**2 - 4 * A * C

        # If the discriminant is negative, no real solution: can't intercept
        if discriminant < 0:
            return target_object.pos

        # Solve the quadratic
        sqrt_disc = np.sqrt(discriminant)
        t1 = (-B + sqrt_disc) / (2 * A)
        t2 = (-B - sqrt_disc) / (2 * A)

        # Pick the smallest positive time (i.e., earliest future intercept)
        t = min([t for t in [t1, t2] if t > 0], default=None)

        # If there's no valid (positive) time, return target's current position
        if t is None:
            return target_object.pos

        # Calculate intercept point: target's position at time t
        P = target_object.pos + target_speed * d * t
        return P


        
class BehaviorStates:
    IDLE = "idle"
    PATROLLING = "patrolling"
    DEFENDING = "defending"
    ATTACKING = "attacking"
    RETREAT = "retreat"
    WANDER = "wander"
    DODGE = "dodge"

class TargetingStates:
    SEARCHING = "searching"
    TARGETING = "targeting"


    