

coordinat_list = [(1,1),(2,2),(3,3),(4,4)]


def corners_to_cornerlist():
    new_coordinat_list = []
    length = len(coordinat_list)

    for i in range(length-1):
        new_coordinat_list.append((coordinat_list[i], coordinat_list[i+1]))
    new_coordinat_list.append((coordinat_list[-1], coordinat_list[0]))
        
        
print(new_coordinat_list)