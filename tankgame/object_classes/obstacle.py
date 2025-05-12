import utils.helper_functions as helper_functions

class Obstacle:
    _id_counter = 0 
    def __init__(self, corners_list, obstacle_type):
        self.corners = corners_list
        self.obstacle_type = obstacle_type
        
        # Obstacle id
        self.id = Obstacle._id_counter
        Obstacle._id_counter += 1
        
    def get_corner_pairs(self):
        # Convert the polygon corners to pairs representing each line in the polygon
        return helper_functions.coord_to_coordlist(self.corners)