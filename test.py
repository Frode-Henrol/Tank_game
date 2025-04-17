

from utils.deflect import line_intersection as line_slow
from utils import line_intersection
import time

# Define input for testing (you can adjust these coordinates)
line_1_start = (0, 0)
line_1_end = (1, 1)
line_2_start = (0, 1)
line_2_end = (1, 0)

# Input for the first function (line_slow)
input_slow = (line_1_start, line_1_end, line_2_start, line_2_end)

# Input for the second function (line_intersection)
input_fast = (line_1_start[0], line_1_start[1], line_1_end[0], line_1_end[1], 
              line_2_start[0], line_2_start[1], line_2_end[0], line_2_end[1])

# Benchmark line_slow function over 10,000 iterations
start_time = time.time()
for _ in range(1000000):
    result_slow = line_slow(*input_slow)
time_slow = time.time() - start_time

# Benchmark line_intersection function over 10,000 iterations
start_time = time.time()
for _ in range(1000000):
    result_fast = line_intersection.line_intersection(*input_fast)
time_fast = time.time() - start_time

# Output the results
print(f"Slow function result: {result_slow}, Time taken for 10,000 iterations: {time_slow:.6f} seconds")
print(f"Fast function result: {result_fast}, Time taken for 10,000 iterations: {time_fast:.6f} seconds")
