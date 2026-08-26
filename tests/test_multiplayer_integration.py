"""Automated integration test for host/join multiplayer.

Runs two real TankGame instances in one process (host + client), connects them over real
UDP sockets on loopback, and drives many ticks of the actual host_apply_client_inputs() /
update() / host_broadcast_snapshot() / client_apply_snapshot() methods used by playing().
Asserts the client's local mirror of every tank converges on the host's authoritative state -
including AI-controlled tanks, which only ever run on the host.

This is a controlled, deterministic driver (each tick: send input, wait for it to arrive,
apply; simulate; broadcast; wait for it to arrive, apply) rather than a realistic concurrent
timing simulation - it's here to catch correctness bugs in the sync logic, not timing/jitter
behavior.

Run directly: `python tests/test_multiplayer_integration.py`
"""

import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import tankgame  # noqa: E402  (forces `tankgame` to resolve as the package before tankgame_dir is added below)
sys.path.insert(0, os.path.join(REPO_ROOT, "tankgame"))

import pygame as pg  # noqa: E402
from tankgame.tankgame import TankGame  # noqa: E402
from tankgame.object_classes.tank import Tank  # noqa: E402
from tankgame.object_classes.obstacle import Obstacle  # noqa: E402

MULTIPLAYER_MAP = os.path.join(REPO_ROOT, "tankgame", "map_files", "multiplayer_test.txt")
PORT = 7798
TICKS = 300
POS_TOLERANCE = 0.01


def wait_until(predicate, timeout=2.0, interval=0.002):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def fresh_multiplayer_game():
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game = TankGame()
    game.clear_all_map_data()
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game.load_map(MULTIPLAYER_MAP)
    game.load_map_textures()
    # update_delta_time() is normally called every real frame from run(); we drive ticks manually
    # here, so pin delta_time to the same fixed step it always resolves to (fixed_delta_time=True),
    # instead of leaving it at __init__'s placeholder value of 1 (a full second per tick).
    game.delta_time = game.fixed_delta_time_step
    return game


def keys(pressed: dict):
    """A pg.key.get_pressed()-like stand-in: any key not in `pressed` reads as False."""
    class Keys:
        def __getitem__(self, k):
            return pressed.get(k, False)
    return Keys()


def main():
    host_game = fresh_multiplayer_game()
    client_game = fresh_multiplayer_game()

    assert len(host_game.units_player_controlled) == 2
    assert len(client_game.units_player_controlled) == 2
    assert [u.id for u in host_game.units] == [u.id for u in client_game.units], \
        "host and client must assign identical ids to identical map units"

    host_game.network.start_host(username="Host", port=PORT)
    client_game.network.start_client(host_ip="127.0.0.1", username="Client", port=PORT)

    assert wait_until(lambda: client_game.network.client_id != 0), "client never received an id from host"
    client_game.player_controlled_tank_num = client_game.network.client_id
    print(f"OK: client assigned client_id={client_game.network.client_id}, "
          f"controls units_player_controlled[{client_game.player_controlled_tank_num}]")

    client_tank_host_side = host_game.units_player_controlled[client_game.player_controlled_tank_num]
    client_tank_client_side = client_game.units_player_controlled[client_game.player_controlled_tank_num]
    assert client_tank_host_side.id == client_tank_client_side.id

    host_own_tank = host_game.units_player_controlled[0]
    start_pos = tuple(client_tank_host_side.pos)

    # Simulate the client holding "rotate right + move forward", aiming at a fixed point -
    # drives real Tank.rotate()/move() on the host's proxy of the client's tank every tick.
    fake_keys = keys({pg.K_d: True, pg.K_w: True})
    fake_mouse_buttons = [False, False, False]
    fake_mouse_pos = (900, 500)

    for tick in range(TICKS):
        client_game.client_send_input(fake_keys, fake_mouse_buttons, fake_mouse_pos)
        assert wait_until(lambda: len(host_game.network.input_from_clients) > 0), f"tick {tick}: host never received client input"

        # Capture "previous" state before triggering the send, so the freshness check below can't
        # race against the background recv thread already having stored this tick's packet.
        prev_snapshot = client_game.network.snapshot_from_host

        host_game.host_apply_client_inputs()
        host_game.update()
        host_game.host_broadcast_snapshot()

        assert wait_until(lambda: client_game.network.snapshot_from_host is not prev_snapshot), \
            f"tick {tick}: client never received a fresh snapshot from host"
        client_game.client_apply_snapshot()

    moved_distance = ((client_tank_host_side.pos[0] - start_pos[0]) ** 2 +
                       (client_tank_host_side.pos[1] - start_pos[1]) ** 2) ** 0.5
    print(f"OK: client-controlled tank moved {moved_distance:.1f}px on the host over {TICKS} ticks "
          f"(driven purely by network input)")
    assert moved_distance > 10, "client-controlled tank barely moved on the host - input wasn't applied"

    # Every tank's client-side mirror must match the host's authoritative state, including
    # AI-controlled bots (simulated only on the host, never on the client).
    for host_unit in host_game.units:
        client_unit = client_game.units_dict[host_unit.id]
        dx = abs(client_unit.pos[0] - host_unit.pos[0])
        dy = abs(client_unit.pos[1] - host_unit.pos[1])
        assert dx < POS_TOLERANCE and dy < POS_TOLERANCE, (
            f"tank id={host_unit.id} diverged: host={host_unit.pos} client={client_unit.pos}"
        )
        assert client_unit.dead == host_unit.dead, f"tank id={host_unit.id} dead-state diverged"
    print(f"OK: all {len(host_game.units)} tanks (player + AI) converged to identical position/dead-state "
          f"between host and client after {TICKS} ticks")

    assert abs(host_own_tank.pos[0] - client_game.units_dict[host_own_tank.id].pos[0]) < POS_TOLERANCE
    print("OK: host's own tank (never touched by client input) also mirrors correctly")

    host_game.network.stop()
    client_game.network.stop()
    print("\nALL MULTIPLAYER INTEGRATION CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
