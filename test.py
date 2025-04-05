
from utils import deflect as df

def deflect_ray(obstacles, bounces, start_point, direction):

    projectile_path_scale = 10
    bounce_count = 0
    lines = []
    
    found_line = False

    
    while True:
        
        if bounce_count == bounces:
            break
        
        projectile_path_scale += 50
        
        end_point = (start_point[0] + direction[0] * projectile_path_scale,
                    start_point[1] + direction[1] * projectile_path_scale)

        for obstacle in obstacles:
            for corner_pair in obstacle.get_corner_pairs(): 
                    
                # Find coord where projectile and line meet
                intersect_coord = df.line_intersection(corner_pair[0], corner_pair[1], start_point, end_point)

                # If there is no intersection continue
                if intersect_coord == None:
                    continue
                
                # Find normal vector of line
                normal_vector1, normal_vector2 = df.find_normal_vectors(corner_pair[0], corner_pair[1])

                # Find deflection vector and update the direction vector
                dot1 = normal_vector1[0]*direction[0] + normal_vector1[1]*direction[1]

                # The dot product should be negative if it is facing the projectile.   (Lige pt virker det ligemeget hvilken normalvector der vælges)
                if dot1 < 0: chosen_normal = normal_vector1
                else: chosen_normal = normal_vector2
                
                lines.append((start_point,intersect_coord))
                
                # Now do the reflection/deflection with chosen_normal
                direction = df.find_deflect_vector(chosen_normal, direction)
                start_point = intersect_coord
                bounces += 1
                found_line = True
                break
            
            if found_line:
                break
               
                
    return lines
