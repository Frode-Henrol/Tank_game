import tankgame.utils.networking as networking


nt = networking.Multiplayer()

inp = input("HOSTING? 0 or 1")
inp = int(inp)


if inp == 0:
    nt.start_client(host_ip="127.0.0.1", username="Client")
else:       
    nt.start_host("Host")


itera = 0
inner_it = 0
while True:
    itera +=1
    
    # Client
    if inp == 0:
        nt.host_to_client_send
        tanks = [
            (1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, True, False)
        ]
        
        nt.client_to_host_send(tanks)
        
        if nt.tank_data_from_host:
            if itera % 30000 == 0:
                inner_it += 1
                print(inner_it)
                print(nt.tank_data_from_host)
        
    # Host  
    if inp == 1:
        tanks = [
            (1, 10.0, 20.0, 30.0, 40.0, 0.1, 0.2, True, False),
            (2, 15.0, 25.0, 35.0, 45.0, 0.3, 0.4, False, True),
        ]
        
        nt.host_to_clients_send(tanks)

        if nt.tank_data_from_clients:
            if itera % 30000 == 0:
                inner_it += 1
                print(inner_it)
                print(nt.tank_data_from_clients)
                
                
    def multiplayer_run_playing_old(self):
        
        # IF HOSTING
        if self.hosting_game and not self.joined_game:
            
            # Only send if we have any units
            if self.units:
                # Send all unit data to clients
                all_unit_data = [self.extract_unit_info(unit) for unit in self.units]
                self.network.host_to_clients_send(all_unit_data) # To not send the clients own data the host_clients_send need to be modified or logic moved out in this loop
                
        # IF JOINING (CLIENT)
        if self.joined_game and not self.hosting_game:
            print(f"{self.player_controlled_tank_num=}")
            
              # Make sure we have player controlled tanks and a valid index
            if self.units_player_controlled and 0 <= self.player_controlled_tank_num < len(self.units_player_controlled):
            # Send client controlled unit data to host
                client_unit = self.units_player_controlled[self.player_controlled_tank_num]
                client_unit_data = self.extract_unit_info(client_unit)
                self.network.client_to_host_send([client_unit_data])

            
            # Receive unit data fom host
            host_unit_data_list = self.network.tank_data_from_host
            
            # Receive unit data from host
            host_unit_data_list = self.network.tank_data_from_host
            
            for unit_data in host_unit_data_list:
                tank_id = unit_data[0]  # First element is the tank ID
                # if tank_id == self.network.client_id:
                #     continue
                
                # Get the corresponding unit from the dictionary
                unit = self.units_dict.get(tank_id)
                if unit is None:
                    continue  # Skip if unit doesn't exist
                    
                # Update unit properties from received data
                unit.pos = (unit_data[1], unit_data[2])  # pos_x, pos_y
                unit.aim_pos = (unit_data[3], unit_data[4])  # aim_x, aim_y
                unit.degrees = unit_data[5]  # body_angle
                unit.turret_rotation_angle = unit_data[6]  # turret_angle
                
                # Handle shooting if needed
                if unit_data[7] == 1:  # Shot fired
                    unit.shoot(unit.aim_pos)
                    
                if unit_data[8] == 1:
                    unit.lay_mine() # Mine layed
