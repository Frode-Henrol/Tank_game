import struct

HEADER_FORMAT = '<I'
TANK_FORMAT = '<i f f f f f f ? ?'

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
TANK_SIZE = struct.calcsize(TANK_FORMAT)

def pack_all_tanks(tank_list: list) -> bytes:
    """Pack tanks list"""
    header = struct.pack(HEADER_FORMAT, len(tank_list))
    body = b''.join(struct.pack(TANK_FORMAT, *tank) for tank in tank_list)
    return header + body

def unpack_all_tanks(data: bytearray) -> list:
    """Unpack tanks list"""
    num_tanks = struct.unpack_from(HEADER_FORMAT, data, 0)[0]
    tanks = []
    for i in range(num_tanks):
        offset = HEADER_SIZE + i * TANK_SIZE
        tank_data = struct.unpack_from(TANK_FORMAT, data, offset)
        tanks.append(tank_data)
    return tanks




