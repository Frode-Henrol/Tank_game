# cython: boundscheck=False, wraparound=False, nonecheck=False

cdef double EPSILON = 1e-9

def line_intersection(double x1, double y1, double x2, double y2,
                      double x3, double y3, double x4, double y4):
    cdef double x1_min, x1_max, y1_min, y1_max
    cdef double x3_min, x3_max, y3_min, y3_max
    cdef double denominator, det1, det2, px, py

    # Precompute bounding box edges
    if x1 < x2:
        x1_min, x1_max = x1, x2
    else:
        x1_min, x1_max = x2, x1

    if y1 < y2:
        y1_min, y1_max = y1, y2
    else:
        y1_min, y1_max = y2, y1

    if x3 < x4:
        x3_min, x3_max = x3, x4
    else:
        x3_min, x3_max = x4, x3

    if y3 < y4:
        y3_min, y3_max = y3, y4
    else:
        y3_min, y3_max = y4, y3

    # Early bounding box rejection
    if x1_max < x3_min or x1_min > x3_max or y1_max < y3_min or y1_min > y3_max:
        return -1.0, -1.0

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denominator == 0.0:
        return -1.0, -1.0

    det1 = x1 * y2 - y1 * x2
    det2 = x3 * y4 - y3 * x4

    px = (det1 * (x3 - x4) - (x1 - x2) * det2) / denominator
    py = (det1 * (y3 - y4) - (y1 - y2) * det2) / denominator

    if (x1_min - EPSILON <= px <= x1_max + EPSILON and
        y1_min - EPSILON <= py <= y1_max + EPSILON and
        x3_min - EPSILON <= px <= x3_max + EPSILON and
        y3_min - EPSILON <= py <= y3_max + EPSILON):
        return px, py

    return -1.0, -1.0
