import struct

HEADER_FORMAT = '<I'             # Unsigned int: number of tanks
TANK_FORMAT = '<i f f f f f f ? ?'  # id, pos_x, pos_y, aim_x, aim_y, body_angle, turret_angle, shot_fired, mine_layed

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
TANK_SIZE = struct.calcsize(TANK_FORMAT)


def pack_all_tanks(tank_list):
    """
    tank_list: list of tuples in the format
        (id: int,
         pos_x: float, pos_y: float,
         aim_x: float, aim_y: float,
         body_angle: float, turret_angle: float,
         shot_fired: bool, mine_layed: bool)
    """
    header = struct.pack(HEADER_FORMAT, len(tank_list))
    body = b''.join(struct.pack(TANK_FORMAT, *tank) for tank in tank_list)
    return header + body

def unpack_all_tanks(data):
    num_tanks = struct.unpack_from(HEADER_FORMAT, data, 0)[0]
    tanks = []
    for i in range(num_tanks):
        offset = HEADER_SIZE + i * TANK_SIZE
        tank_data = struct.unpack_from(TANK_FORMAT, data, offset)
        tanks.append(tank_data)
    return tanks

# Example tank list
tanks = [
    (1, 10.0, 20.0, 30.0, 40.0, 0.1, 0.2, True, False),
    (2, 15.0, 25.0, 35.0, 45.0, 0.3, 0.4, False, True),
]

# Pack
msg = pack_all_tanks(tanks)
print(f"{msg=}")

# Simulate sending and receiving
received = msg

# Unpack
decoded = unpack_all_tanks(received)
print(f"{decoded=}")
# decoded is a list of tuples per tank
