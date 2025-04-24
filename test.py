
def update(self):        
    
    dt = 1/60
    
    self.frame += 1
    self.time += dt
        
        
    # Debug output
    # if random.random() < 0.01:  # Print about 1% of frames to avoid spam
    #     print(f"Delta: {dt:.10f}, FPS: {1/dt:.1f} ")
    
    # Track marks logic
    self.track_counter += 60 * dt
    if self.track_counter >= self.track_interval:
        self.track_counter = 0
        for unit in self.units:
            unit.send_delta(dt) # Send delta time to tank instances
            
            if not unit.dead and unit.is_moving:
                # Add track mark at tank's position
                track_pos = unit.pos
                track_angle = unit.degrees + 90
                self.tracks.append(Track(tuple(track_pos), track_angle, self.track_img, lifetime=1/dt))

    # Update and remove old tracks
    self.tracks = [track for track in self.tracks if track.update(dt*60)]
    
    # Temp list is created and all units' projectiles are added to a single list
    temp_projectiles = []
    for unit in self.units:
        unit.update(dt)
        temp_projectiles.extend(unit.projectiles)

    for mine in self.mines:
        mine.update(dt)
    
    # Update projectiles and handle collisions
    for unit in self.units:
        for i, proj in enumerate(unit.projectiles):
            
            proj.set_delta_time(dt) # Send frame delta time
            proj.update()                   # Update the projectile
            
            for obstacle in self.obstacles:
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
            unit.ai.projectiles = self.projectiles

        # Check unit/surface collisions
        for obstacle in self.obstacles:
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
                self.mines.remove(mine)
            mine.get_unit_list(self.units)
            mine.check_for_tank(unit)

    self.projectiles = temp_projectiles
