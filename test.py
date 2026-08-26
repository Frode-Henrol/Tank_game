"""Automated smoke test for the UDP multiplayer transport (tankgame/utils/networking.py).

Spins up a host and a client Multiplayer() over loopback in-process, exchanges a few
input/snapshot messages, and asserts they arrive decoded correctly on the other side.
Run directly: `python test.py`
"""

import os
import sys
import time
import tankgame.utils.networking as networking


def wait_until(predicate, timeout=2.0, interval=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def main():
    port = 7799  # avoid clashing with a real game session on the default port

    host = networking.Multiplayer()
    host.start_host(username="Host", port=port)

    client = networking.Multiplayer()
    client.start_client(host_ip="127.0.0.1", username="Client", port=port)

    assert wait_until(lambda: client.client_id != 0), "Client never received an id from the host"
    print(f"OK: client received id {client.client_id}")

    assert wait_until(lambda: port_addr_present(host)), "Host never registered the joining client"
    print("OK: host registered the client")

    client_input = {
        "type": "input",
        "tank_id": 1,
        "directional": False,
        "move_fwd": True, "move_back": False,
        "rotate_left": False, "rotate_right": True,
        "aim_x": 123.0, "aim_y": 456.0,
        "fire": True, "mine": False, "reload": False,
    }
    client.client_to_host_send(client_input)

    assert wait_until(lambda: bool(host.input_from_clients)), "Host never received the client's input packet"
    received_input = next(iter(host.input_from_clients.values()))
    assert received_input == client_input, f"Input payload mismatch: {received_input} != {client_input}"
    print("OK: host received and correctly decoded client input")

    host_snapshot = {
        "type": "snapshot",
        "tanks": [{"id": 1, "x": 10.0, "y": 20.0, "degrees": 90.0, "turret": 45.0, "dead": False, "shot_counter": 3}],
        "projectiles": [{"uid": 7, "x": 1.0, "y": 2.0, "dir_x": 1.0, "dir_y": 0.0, "bounce_count": 0}],
        "mines": [],
        "obstacles_des_alive": [0, 1, 2],
    }
    host.host_to_clients_send(host_snapshot)

    assert wait_until(lambda: client.snapshot_from_host is not None), "Client never received the host's snapshot"
    assert client.snapshot_from_host == host_snapshot, f"Snapshot payload mismatch: {client.snapshot_from_host} != {host_snapshot}"
    print("OK: client received and correctly decoded host snapshot")

    host.stop()
    client.stop()
    print("\nAll networking transport checks passed.")

    # The host/client recv loops are daemon threads blocked in a blocking recvfrom() call; closing
    # their sockets above makes that call raise (logged, harmless) rather than return, so the threads
    # exit on their own shortly after. Force an immediate, clean process exit rather than waiting on
    # normal interpreter shutdown, which can race with those threads tearing down and print noise.
    sys.stdout.flush()
    os._exit(0)


def port_addr_present(host):
    return len(host.clients_meta) > 0


if __name__ == "__main__":
    main()
