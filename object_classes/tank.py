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
                 image, 
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
        self.image = image
        self.death_image = death_image
        self.active_image = image
        
        # Projectiles from current tank
        self.projectiles: list[Projectile] = []
        
        # Use turret?
        self.use_turret = use_turret
        
        # Pathfinding and waypoint logic
        self.go_to_waypoint = False     # Bool to control if tanks should follow waypoint queue
        self.movement_state = MovementState.IDLE    # Tank states for pathfinding (NOT USED AT THE MOMENT) skal rettes
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
        
        # TEMP: constant to make sure tank image points right way
        tank_correct_orient = -90
        rotated_image = pg.transform.rotate(self.active_image, -self.degrees+tank_correct_orient)
        rect = rotated_image.get_rect(center=self.pos)
        surface.blit(rotated_image, rect.topleft)
        
        
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
               
    def shoot(self, aim_pos):
        if self.dead and not self.godmode:
            return
        if len(self.projectiles) >= self.projectile_limit:
            return
        if self.cannon_cooldown == 0:
            self.cannon_cooldown = self.firerate * 5
            # At the moment the distance is hard coded, IT must be bigger than hit box or tank will shot itself.
            spawn_distance_from_middle = 30
            
            if self.use_turret:
                
                # Find the unit vector between mouse and tank. This is the projectile unit direction vector
                unit_direction = helper_functions.unit_vector(self.pos, aim_pos)
                projectile_direction = unit_direction
                
                print(f"{aim_pos=} {unit_direction=}")
            else:
                # Calculate magnitude scalar of units direction vector
                magnitude_dir_vec = helper_functions.get_vector_magnitude(self.direction)
                
                # Find unit vector for direction
                unit_direction = (self.direction[0]/magnitude_dir_vec, self.direction[1]/magnitude_dir_vec)
                
                projectile_direction = self.direction
                    
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
                if self.left_turn(self.pos, pos_dir, node_coord):
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
        
    def left_turn(self, p: tuple, q: tuple, r: tuple) -> bool:
        # Check if coord r is to left of right of line p-q
        return (q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]) >= 0
        

class TankAI:
    def __init__(self, tank: Tank, personality, valid_nodes: list[tuple], units: list[Tank], obstacles: list[Obstacle], projectiles: list[Projectile]):
        self.tank = tank  # The tank instance this AI controls
        self.personality = personality
        self.state = States.KEEP_DISTANCE  # Default state
        self.target = None  # Target for attack/movement
        self.valid_nodes = valid_nodes
        self.valid_nodes_original = valid_nodes.copy()
        
        # Other units on map without the controlled tank
        self.units = units
        self.units.remove(self.tank) # skal rettes, fjern egen tank fra listen
        
        # All polygons/obstacles on the map: Excluding the border polygon
        self.obstacles = obstacles
        
        # All projectiles from the map
        self.projectiles = projectiles
        
        # Check if tanks has no speed
        if self.tank.speed == 0:
            self.movement = False 
        self.movement = True
        
        # Tank that is under targeting
        self.targeted_unit = None
        self.targeted_unit = self.units[0] # TEST using player as hardcoded target
        self.unit_target_line = None
        self.unit_target_line_color = (255, 182, 193)
        self.target_in_sight = False
        
        # Min and max distance to for keep distance behavior
        self.max_dist_limit = 1000
        self.min_dist_limit = 0
        
        self.max_dist = self.max_dist_limit 
        self.min_dist = self.min_dist_limit
        
        # Min distance for triggering dogde behavior
        self.dogde_distance = 300
        self.dodging_active = False
        
        # Controls how often we do a update
        self.frame_counter = 0
        self.update_frame_count = 30
        
        # Test optimizing:
        self.valid_nodes = np.array(valid_nodes)  # Convert list to NumPy array
        self.kd_tree = KDTree(self.valid_nodes)  # Build KD-Tree
        self.possible_nodes = []
        
    def update(self):
        self.frame_counter += 1
        """Update AI behavior based on state."""
        
        # Everything inside if state is ran less often
    
        if self.state ==  States.IDLE:
            self.idle_behavior()
        elif self.state == States.PATROLLING:
            self.patrol_behavior()
        elif self.state == States.CHASING:
            self.chase_behavior()
        elif self.state == States.ATTACKING:
            self.attack_behavior()
        elif self.state == States.RANDOM:
            self.random_behavior()
        elif self.state == States.KEEP_DISTANCE:
            self.keep_distance_behavior()       # Should maybe be renamed to chase behavior
        
        if self.frame_counter % self.update_frame_count == 0:
            # Run hit scan check
            self.hit_scan_check()
        
        if self.frame_counter % 60 == 0:
            if not self.target_in_sight:
                self.decrease_min_dist()
            elif self.target_in_sight:
                self.increase_min_dist()
                
            print(f"Min dist: {self.min_dist} Max dis: {self.max_dist}")

            self.update_target_distance()
            self.max_dist_update()
            
        # Shooting logic
        self.shooting()
        
        # Check for dogde:
        # self.dodging()
            
            
        self.misc_update()

    def misc_update(self):
        if not self.target_in_sight:
            self.unit_target_line_color = (255, 182, 193)
        else:
            self.unit_target_line_color = (144, 238, 144)
            
    def shooting(self):
        self.unit_target_line = self.tank.pos, self.targeted_unit.pos
        shooting_chance = random.randint(0,1000)
        
        if shooting_chance < 250 and self.target_in_sight:
            # Find the unit vector between mouse and tank. This is the projectile unit direction vector
            self.tank.shoot(self.targeted_unit.pos)
    
    def dodging(self):
        
        temp_proj_data = [] # unsuded
        
        # Check for projectiles close to tank
        for proj in self.projectiles:
            dist = helper_functions.distance(proj.pos, self.tank.pos)
            if dist < self.dogde_distance:
                print(f"Trying to dodge")
                self.random_behavior()
                
                #self.dodging_active = False
            
  
    def idle_behavior(self):
        """Do nothing or look around."""

        dist = helper_functions.distance(self.tank.pos, self.targeted_unit.pos)
        
        if not self.target_in_sight:
            if self.min_dist > dist and self.tank.go_to_waypoint == False:
                self.state = States.KEEP_DISTANCE
            elif self.max_dist < dist and self.tank.go_to_waypoint == False:
                self.state = States.KEEP_DISTANCE
        elif self.target_in_sight and self.state == States.IDLE:
            # If target is in sight we abort current waypoint
            

            self.tank.abort_waypoint()
            

    def patrol_behavior(self):
        """Move around randomly or along a set path."""
        pass

    def chase_behavior(self):
        """Move toward the player or target."""
        pass

    def attack_behavior(self):
        """Shoot at the player or another enemy."""
        self.tank.shoot()
        
    def random_behavior(self):
        """Move to a random location but only if the previous path is completed."""
        if self.tank.go_to_waypoint == True:  # If already following a path, don't pick a new one
            return
        
        rand_index = random.randint(0, len(self.valid_nodes) - 1)  # Fix out-of-bounds error
        valid_node = self.valid_nodes[rand_index]

        self.tank.find_waypoint(valid_node)
        
        self.state = States.IDLE
        
    def keep_distance_behavior(self):
        """Move to a location that keeps the tank within the min and max distance from the player.
        If the player moves too far away, approach them."""
        if self.tank.go_to_waypoint:
            return  # If already moving, do nothing

        # Build a KD-tree for fast nearest-neighbor search
        kd_tree = KDTree(self.valid_nodes)
        
        # Query KD-tree for nodes within min_dist and max_dist from target
        target_pos = self.targeted_unit.pos
        nearby_indices = kd_tree.query_ball_point(target_pos, self.max_dist)
        
        possible_nodes = []
        for idx in nearby_indices:
            node = self.valid_nodes[idx]
            dist_node_target = helper_functions.distance(node, target_pos)
            dist_node_unit = helper_functions.distance(node, self.tank.pos)

            if self.min_dist < dist_node_target < self.max_dist:
                possible_nodes.append((node, dist_node_target, dist_node_unit))

        # If there are valid choices, move to the best one
        amount_nodes = 1  # How many nodes should be randomly chosen (permanent 1?)
        possible_nodes = heapq.nsmallest(amount_nodes, possible_nodes, key=lambda x: x[2])
        
        # for node in possible_nodes:
        #     path = self.tank.find_path(node)
        #     len(path) # TODO

        print(f"Test possible nodes: {possible_nodes}")
        if possible_nodes:
            chosen_node = random.choice(possible_nodes)
            self.tank.find_waypoint(chosen_node[0])

        print(f"Possible nodes for AI: {len(possible_nodes)}")
        self.state = States.IDLE
        self.possible_nodes = [x[0] for x in possible_nodes]
  
    def keep_distance_behavior2(self):
        """Move to a location that keeps the tank within the min and max distance from the player.
        If the player moves too far away, approach them."""
        if self.tank.go_to_waypoint:
            return  # If already moving, do nothing
        
        # Filter valid nodes based on distance criteria
        possible_nodes = []
        
        for node in self.valid_nodes:
            dist_node_target = helper_functions.distance(node, self.targeted_unit.pos)  # Distance from node to target tank
            dist_node_unit = helper_functions.distance(node, self.tank.pos)    # Distance from node to current unit
            #path = self.tank.find_path(node)
            
            if self.max_dist > dist_node_target > self.min_dist:
                possible_nodes.append((node,dist_node_target,dist_node_unit))
        
        # If there are valid choices, move to a random one
        amount_nodes = 1 # How many nodes should be randomly choosen between SKAL RETTES MÅSKE PERMENENT 1?
        possible_nodes = sorted(possible_nodes, key=lambda x: x[2])[:amount_nodes]  # Sorts all valid nodes based on what is closest to the tank
        print(f"Test possible nodes: {possible_nodes}")
        if possible_nodes:
            chosen_node = random.choice(possible_nodes)
            self.tank.find_waypoint(chosen_node[0])
                
        print(f"Possible nodes for ai: {len(possible_nodes)}")
        self.state = States.IDLE
        self.possible_nodes = [x[0] for x in possible_nodes]

    # TEST _ MIGHT BE TRASH skal rettes 
    def decrease_min_dist(self):
        if self.min_dist - 50 > self.min_dist_limit:
            self.min_dist -= 50
        
    def increase_min_dist(self):
        if self.min_dist + 50 < self.max_dist_limit:
            self.min_dist += 50
            
    def max_dist_update(self):
        self.max_dist = self.min_dist + 50  # The 200 is hardcoded you can call difference between min and max

    def change_state(self, new_state):
        """Change the AI state."""
        self.state = new_state

    def hit_scan_check(self):
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
        
    def update_target_distance(self):
        coord1, coord2 = self.unit_target_line
        self.target_distance = helper_functions.distance(coord1, coord2)

class States:
    IDLE = "idle"
    PATROLLING = "patrolling"
    CHASING = "chasing"
    ATTACKING = "attacking"
    RANDOM = "random"
    KEEP_DISTANCE = "keepdistance"
    
    
class MovementState:
    ROTATING = "rotating"
    MOVING = "moving"
    IDLE = "idle"
    