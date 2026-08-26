"""Automated test for dynamic 1/2/3-player spawning based on actual lobby size.

Checks the injection logic in isolation for player_count 1/2/3 (a solo host gets exactly one tank,
not a phantom second player), then drives a real host + two clients through the full handshake and
start_multiplayer_campaign() to confirm the count is computed correctly from actual connections and
that all three player tank texture assets (player1/2/3_tank + turret - blue/red/green) actually load
without error.

Run directly: `python tests/test_multiplayer_player_count.py`
"""

import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import tankgame  # noqa: E402
sys.path.insert(0, os.path.join(REPO_ROOT, "tankgame"))

from tankgame.tankgame import TankGame  # noqa: E402
from tankgame.object_classes.tank import Tank  # noqa: E402
from tankgame.object_classes.obstacle import Obstacle  # noqa: E402

PORT = 7795


def wait_until(predicate, timeout=2.0, interval=0.002):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def fresh_game(hosting=False, joined=False):
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game = TankGame()
    game.hosting_game = hosting
    game.joined_game = joined
    return game


def test_injection_logic_in_isolation():
    game = fresh_game(hosting=True)
    base_unit_list = [((600, 900), 90, 0, 1), ((1200, 950), 270, 7, 2)]  # 1 player spawn + 1 AI bot

    game.multiplayer_player_count = 1
    result = game.inject_multiplayer_player_spawns(base_unit_list)
    player_types = sorted(u[2] for u in result if u[2] in (0, 20, 21))
    assert player_types == [0], f"solo host should get exactly one tank, got types {player_types}"
    print("OK: player_count=1 -> exactly one (blue/player1) tank, no phantom second player")

    game.multiplayer_player_count = 2
    result = game.inject_multiplayer_player_spawns(base_unit_list)
    player_types = sorted(u[2] for u in result if u[2] in (0, 20, 21))
    assert player_types == [0, 20], f"expected blue+red (0,20), got {player_types}"
    print("OK: player_count=2 -> blue + red tanks")

    game.multiplayer_player_count = 3
    result = game.inject_multiplayer_player_spawns(base_unit_list)
    player_types = sorted(u[2] for u in result if u[2] in (0, 20, 21))
    assert player_types == [0, 20, 21], f"expected blue+red+green (0,20,21), got {player_types}"
    print("OK: player_count=3 -> blue + red + green tanks")

    # All extra spawns must be at the exact same position as the original (safe-by-construction placement)
    original_pos = base_unit_list[0][0]
    assert all(u[0] == original_pos for u in result if u[2] in (0, 20, 21))
    print("OK: all injected player spawns share the original spawn's position")


def test_real_three_player_handshake():
    host = fresh_game(hosting=True)
    clients = [fresh_game(joined=True) for _ in range(2)]

    host.network.start_host(username="Host", port=PORT)
    for i, c in enumerate(clients):
        c.network.start_client(host_ip="127.0.0.1", username=f"Client{i+1}", port=PORT)
    for c in clients:
        assert wait_until(lambda c=c: c.network.client_id != 0), "a client never connected"

    assert wait_until(lambda: len(host.network.clients_meta) == 2), "host never registered both clients"

    # Capture "previous" state before triggering the broadcast, so the freshness check below can't
    # race against a client's background recv thread already having stored the new result.
    prev_results = {i: c.network.level_result for i, c in enumerate(clients)}

    host.start_multiplayer_campaign()
    assert host.multiplayer_player_count == 3, f"expected 3 players (host + 2 clients), got {host.multiplayer_player_count}"
    host.playthrough([])  # bootstrap: loads level 1 with 3 injected player spawns, broadcasts outcome="start"

    assert len(host.units_player_controlled) == 3
    print(f"OK: host + 2 clients -> {len(host.units_player_controlled)} tanks spawned "
          f"(loading their textures without error confirms all three player1/2/3_tank assets are present)")

    for i, c in enumerate(clients):
        prev = prev_results[i]
        assert wait_until(lambda c=c, prev=prev: c.network.level_result is not prev), "a client never received the start level_result"
        c.client_handle_level_result()
        assert c.multiplayer_player_count == 3
        assert len(c.units_player_controlled) == 3
        assert sorted(u.id for u in c.units) == sorted(u.id for u in host.units)
    print("OK: both clients mirror the 3-player spawn set with matching tank ids")

    host.network.stop()
    for c in clients:
        c.network.stop()


def main():
    test_injection_logic_in_isolation()
    test_real_three_player_handshake()
    print("\nALL PLAYER-COUNT CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
