import pygame as pg
import utils.deflect as df
from object_classes.projectile import Projectile
from object_classes.obstacle import Obstacle
import utils.helper_functions as helper_functions
import numpy as np
import random
import pathfinding
from scipy.spatial import KDTree
import heapq

class Tank:
    def __init__(self, 
                 startpos: tuple,
                 speed: float,
                 firerate: float,
                 speed_projectile: float,
                 spawn_degress: int,
                 bounch_limit: int, 
                 bomb_limit: int,
                 projectile_limit: int,
                 images, 
                 death_image,
                 use_turret,
                 ai_type = None,
                 godmode = False,
                 draw_hitbox = True):
        
        self.pos = list(startpos)
        self.direction = (0,0)  # Skal rettes
        self.degrees = spawn_degress
        self.speed = speed  # Used to control speed so it wont be fps bound
        
        # Projectile
        self.speed_projectile = speed_projectile # Scale the tanks projectile speed
        self.bounch_limit = bounch_limit
        
        # Bombs (not implemented)
        self.bomb_limit = bomb_limit

        self.current_speed = [0,0]
        self.firerate = firerate
        self.cannon_cooldown = 0
        self.projectile_limit = projectile_limit
        
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

        # AI
        # TEST DIC
        self.ai_type = ai_type  
        
        self.units = []
        
    def init_ai(self, obstacles: list[Obstacle], projectiles: list[Projectile]):
        self.ai = TankAI(self, None, self.valid_nodes, self.units.copy(), obstacles, projectiles) if self.ai_type != "player" else None
    
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
        
        # Remove dead projectiles
        self.projectiles[:] = [p for p in self.projectiles if p.alive]
        
        #AI
        if self.ai and not self.dead:
            self.ai.update()
            
        # Pathfinding / waypoint logic if it is activated
        if self.go_to_waypoint:
            self.move_to_node(self.current_node)
            

    
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
            #self.hitbox = None
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
        self.projectiles.append(projectile)                                                                      
        print(self.direction)

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
    
    def add_direction_vector(self, vec_dir):
        # SKAL RETTES - meget logic burde kunne overføres til move method
        x1, y1 = vec_dir
        x2, y2 = self.pos 
        self.pos = list((x1+x2, y1+y2))
        
        # Move hit box:
        for i in range(len(self.hitbox)):
            x, y = self.hitbox[i]  # Unpack the point
            
            moved_x = x + x1
            moved_y = y + y1
            self.hitbox[i] = (moved_x, moved_y)
        
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
        """Controls the tanks toward the next node in the waypoint"""
        rotate_amount = 5
        # -------------------------------------- Computing angle differens --------------------------------------
        # Compute vector to the target
        to_target = (node_coord[0] - self.pos[0], node_coord[1] - self.pos[1])
        
        # Normalize the target direction vector
        to_target_mag = np.hypot(to_target[0], to_target[1])  # Compute magnitude
        to_target_unit = (to_target[0] / to_target_mag, to_target[1] / to_target_mag)  # Normalize
        
        # Compute dot product
        dot = self.direction[0] * to_target_unit[0] + self.direction[1] * to_target_unit[1]
        
        # Clamp dot product to valid range for acos (this is to prevent floating point numbers errors above 1 and below -1) since acos will give error otherwise
        dot = np.clip(dot, -1.0, 1.0)
        
        # Compute angle difference (in radians)
        angle_diff = np.arccos(dot)

        # Convert to degrees
        angle_diff_deg = np.degrees(angle_diff)
        
        # -------------------------------------- Controlling of tank to a node --------------------------------------
        
        # Make a second point to form the direction line from the tank
        pos_dir = (self.pos[0] + self.direction[0], self.pos[1] + self.direction[1])
        
        TURN_THRESHOLD_MIN = 5  # Stop rotating under this value       
        TURN_THRESHOLD_MAX = 45 # Stop moving forward over this value
        DISTANCE_THRESHOLD = 50 // rotate_amount # Stop moving when within this distance to node
        # Distance to node
        distance_to_node = np.hypot(node_coord[0] - self.pos[0], node_coord[1] - self.pos[1])
        
        if distance_to_node > DISTANCE_THRESHOLD:
            if angle_diff_deg > TURN_THRESHOLD_MIN:
                if helper_functions.left_turn(self.pos, pos_dir, node_coord):
                    self.rotate(rotate_amount) 
                else:
                    self.rotate(-rotate_amount) 
                    
            if TURN_THRESHOLD_MAX > angle_diff_deg:
                    self.move("forward")
                    #print(f"{distance_to_node=}")
        
        else:
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
    def __init__(self, tank: Tank, personality, valid_nodes: list[tuple], units: list[Tank], obstacles: list[Obstacle], projectiles: list[Projectile]):
        
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
        
        # Tank that is under targeting
        self.targeted_unit = None
        
        # Controls how often we do a update
        self.frame_counter = 0
        
        # Starting states
        self.behavior_state = BehaviorStates.IDLE     # NEED TO BE IDLE NORMALLY
        self.targeting_state = TargetingStates.SEARCHING
        
        # No speed means tank will stay in idle state
        if self.tank.speed == 0:
            self.movement = False 
        self.movement = True
        
        # Tank that is under targeting
        self.targeted_unit = self.units[0]              # TEST using player as hardcoded target
        self.unit_target_line = None                    # Init line between target and tank
        self.unit_target_line_color = (255, 182, 193) 
        self.target_in_sight = False
        
        self.dist_to_target_direct = 9999
        self.dist_to_target_path = 9999
        
        
        # Patrol
        self.patrol_radius = 200
        self.dist_leave_patrol = 500
        
        # Defend
        self.dist_leave_defend = 800
        
        # Attack
        self.dist_leave_attack = 200
        
        # Dodge
        self.can_dogde = True
        self.closest_projectile = (None, 9999)
        self.dist_start_dodge = 45
        self.dodge_nodes = []
        self.dodge_cooldown = 0
        
        # Shooting
        self.angle_diff_deg = 9999 # The current angle between target and turret
        
        self.shooting_angle = 5     # Maximum angle to target before firing TODO
        self.rotation_speed = 1     # Degress pr frame
        self.inaccuracy = 200         # 0 is perfect aim and higher values is worse
        
        self.aiming_angle = 15      # The angle which the turret will wander off from target. 
        self.rotation_mult_max = 2  # Maxium rotation multiplier when angledifference is 180 degress
        self.rotation_mult_min = 0.8    # Minimum rotation multiplier when angledifference is 0 degress
        
        self.perfect_aim = False        # Removes random turret wandering
        self.turret_turn_threshold = 2  # Under this angle from target the turret stop moving
        
        self.advandced_targeting = True # Advanced targeting
        
        # Searching
        
        # Patrolling
        
        # Wander
        self.wander_radius = 200
        self.defend_time = 60 * 10
        self.timer = 0
        
        # Test
        self.current_target_angle = None  # Store the randomized target angle
        
    
    def update(self):
        self.frame_counter += 1
        self.misc_updates()
        self.targeting()
        
        if self.behavior_state == BehaviorStates.DODGE:
            self.handle_dodge_state()
            return
        # Behavior movement
        if self.can_dogde and self.closest_projectile[1] < self.dist_start_dodge and self.dodge_cooldown == 0:
            self.behavior_state = BehaviorStates.DODGE
            self.dodge()
            self.dodge_cooldown = 120  # e.g. 30 frames cooldown
            return
    
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
        if self.advandced_targeting:
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
        
        
            
            #self.tank.find_waypoint(self.targeted_unit.pos)
        
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

        dodge_nodes_pot = []
        # Find left and right point (vinkelret) from the closest projectil path
        for dodge_dir in dodge_dirs:
            norm = np.linalg.norm(dodge_dir)
            if norm == 0:
                continue
            dodge_dir = (dodge_dir[0] / norm, dodge_dir[1] / norm)

            for i in range(100, 200, 50):
                target = (
                    self.tank.pos[0] + dodge_dir[0] * i,
                    self.tank.pos[1] + dodge_dir[1] * i
                )
                target = self.tank.convert_node_to_grid(target)     # Convert coords to pathfinding nodes
                dodge_nodes_pot.append(target)

        # Make sure only to use nodes that are valid on the map
        dodge_nodes_valid = list(set(dodge_nodes_pot) & set(self.valid_nodes_original))
        
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
    
    def searching(self):
        # Random movement scanning the surroundings
        pass
    
    def targeting(self):
        
        # Hardcoded target
        target_pos = self.targeted_unit.pos[0], self.targeted_unit.pos[1]
    
        self.move_turret_to_target(target_pos, self.aiming_angle)
            
        #self.tank.shoot(None)
    
    # ======================= Misc functions =======================
    
    def misc_updates(self):
        self.unit_target_line = self.tank.pos, self.targeted_unit.pos
        
        # Direct distance updated every 10 frames
        if self.frame_counter % 10 == 0:
            self.dist_to_target_direct = helper_functions.distance(self.tank.pos, self.targeted_unit.pos)
        
        # CAN BE OPTIMIZED. TODO paths could be saved or threshold for when a new should be calculated could be made
        # Path distance updated every 60 frames
        if self.frame_counter % 60 == 0:
            self.dist_to_target_path = len(self.tank.find_path(self.targeted_unit.pos)) * self.tank.node_spacing 
            
            self.hit_scan_check_proximty()  
        
        if self.timer > 0:
            self.timer -= 1  
        
        self.find_closest_projectile()
            
        if self.dodge_cooldown > 0:
            self.dodge_cooldown -= 1
        
    
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

        #print(f"{rotation_multiplier=}")
        
        # Debug visualization
        self.debug_turret_v = (
            self.tank.pos, 
            (turret_direction[0] * 100 + self.tank.pos[0], turret_direction[1] * 100 + self.tank.pos[1])
        )
        
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

        # If there are valid choices, move to the best one
        amount_nodes = 20  # How many nodes should be randomly chosen (permanent 1?)
        possible_nodes = heapq.nsmallest(amount_nodes, possible_nodes, key=lambda x: x[2])
        
        print(f"Test possible nodes: {possible_nodes}")
        if possible_nodes:
            chosen_node = random.choice(possible_nodes)
            self.tank.find_waypoint(chosen_node[0])
        
        self.possible_nodes = [x[0] for x in possible_nodes]
          
    def hit_scan_check_proximty(self):
        coord1, coord2 = self.unit_target_line 
        for obstacle in self.obstacles:
            for corner_pair in obstacle.get_corner_pairs():
                result = df.line_intersection(map(float,coord1), map(float,coord2), corner_pair[0], corner_pair[1])
                #print(f"Checking intersection: {corner_pair} and {coord1, coord2} -> Result: {result}")
                if result != None:
                    self.target_in_sight = False
                    return False
        
        for unit in self.units:
            if unit.ai == None:     # Skal rettes. Burde have seperate liste for "onde units", pt er det bare dem uden ai
                continue
            
            # Skip dead units
            if unit.dead:
                continue
            # Cheap calculation less accurate: (problem is it check the hitray like it is infinite in bots direction
            # meaning it checks also for tanks behind itself) BUT IT IS MUCH LESS RECKLESS
            min_dist = helper_functions.point_to_line_distance(coord1, coord2, unit.pos)
            tank_width = 45 # skal rettes. PT hardcoded...
            if min_dist < tank_width:
                self.target_in_sight = False
                return False
            
            # # Expensive calculation more accurate: (need higher updaterate to functin best)
            # for corner_pair in unit.get_hitbox_corner_pairs():
            #     result = df.line_intersection(coord1, coord2, corner_pair[0], corner_pair[1])
            #     #print(f"Checking intersection: {corner_pair} and {coord1, coord2} -> Result: {result}")
            #     if result != None:
            #         self.target_in_sight = False
            #         return False
                    
            
        self.target_in_sight = True        
        return True
        
    def find_closest_projectile(self):
        closest = None
        min_dist = float("inf")

        for proj in self.projectiles:
            
            # dist = helper_functions.distance(proj.pos, self.tank.pos)   # Finds direct distance
            print(proj.startpos, proj.pos, self.tank.pos)
            dist = helper_functions.point_to_line_distance(proj.startpos, proj.pos, self.tank.pos)  # Finds distance to proj path
            
            if dist < min_dist:
                min_dist = dist
                closest = proj

        if closest:
            self.closest_projectile = (closest, min_dist)
        else:
            self.closest_projectile = (None, 9999)
            
        
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


    