import pygame as pg
import utils.helper_functions as hf
import numpy as np
import triangle as tr
import heapq
from collections import defaultdict
import time 
import math
from map_grid import MapGrid


polygons, units = hf.load_map_data(r"map_files\map_test1.txt")


grid = MapGrid(polygons, 50)

print(grid.get_mapgrid_dict())
