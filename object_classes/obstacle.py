import utils.helper_functions as helper_functions

class Obstacle:
    
    def __init__(self, corners_list, obstacle_type):
        self.corners = corners_list
        self.obstacle_type = obstacle_type
        
    def get_corner_pairs(self):
        # Convert the polygon corners to pairs representing each line in the polygon
        return helper_functions.coord_to_coordlist(self.corners)