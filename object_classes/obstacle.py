import utils.helper_functions as helper_functions

class Obstacle:
    
    def __init__(self, corners_list):
        self.corners = corners_list
        
    def get_corner_pairs(self):
        # Convert the polygon corners to pairs representing each line in the polygon
        return helper_functions.coord_to_coordlist(self.corners)