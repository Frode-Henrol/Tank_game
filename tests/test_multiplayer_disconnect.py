"""Automated test for mid-game disconnect detection.

Connects a real host+client pair on the multiplayer test map, then simulates a client going silent
(backdating its last-seen timestamp rather than actually waiting DISCONNECT_TIMEOUT seconds, since
the logic under test is a plain time.time() comparison already timing-verified elsewhere for the
join-retry path) and asserts: the host's stale_client_ids()/host_broadcast_snapshot() correctly flag
that tank, the client mirrors the flag via a normal snapshot, and the symmetric client-side
host_connection_lost() check works the same way in the other direction.

Run directly: `python tests/test_multiplayer_disconnect.py`
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

import tankgame.utils.networking as networking  # noqa: E402
from tankgame.tankgame import TankGame  # noqa: E402
from tankgame.object_classes.tank import Tank  # noqa: E402
from tankgame.object_classes.obstacle import Obstacle  # noqa: E402

MULTIPLAYER_MAP = os.path.join(REPO_ROOT, "tankgame", "map_files", "multiplayer_test.txt")
PORT = 7796


def wait_until(predicate, timeout=2.0, interval=0.002):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


class NoKeysPressed:
    """A pg.key.get_pressed()-like stand-in where every key reads as False."""
    def __getitem__(self, k):
        return False


def fresh_game(hosting=False, joined=False):
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game = TankGame()
    game.hosting_game = hosting
    game.joined_game = joined
    game.clear_all_map_data()
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game.load_map(MULTIPLAYER_MAP)
    game.load_map_textures()
    game.delta_time = game.fixed_delta_time_step
    return game


def main():
    host = fresh_game(hosting=True)
    client = fresh_game(joined=True)

    host.network.start_host(username="Host", port=PORT)
    client.network.start_client(host_ip="127.0.0.1", username="Client", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected"
    client.player_controlled_tank_num = client.network.client_id
    client_addr = next(iter(host.network.clients_meta.keys()))
    client_tank_id = host.units_player_controlled[client.network.client_id].id

    # A real input packet so the host has a _last_seen entry to backdate
    client.client_send_input(keys=NoKeysPressed(), mouse_buttons=[False, False, False], mouse_pos=(0, 0))
    assert wait_until(lambda: client_addr in host.network._last_seen), "host never recorded the client's input"

    assert host.network.stale_client_ids() == set(), "client should not be flagged stale right after a fresh packet"

    # Simulate DISCONNECT_TIMEOUT+ seconds of silence without actually waiting that long
    host.network._last_seen[client_addr] -= (networking.DISCONNECT_TIMEOUT + 1)

    stale = host.network.stale_client_ids()
    assert stale == {client.network.client_id}, f"expected client id {client.network.client_id} flagged stale, got {stale}"
    print("OK: host correctly flags a silent client as stale")

    host.host_broadcast_snapshot()
    disconnected_unit = host.units_dict[client_tank_id]
    assert disconnected_unit.net_disconnected is True, "host's own tank object should be flagged too (for its own screen)"

    prev_snapshot = client.network.snapshot_from_host
    assert wait_until(lambda: client.network.snapshot_from_host is not prev_snapshot), "client never received the snapshot"
    client.client_apply_snapshot()

    client_mirror = client.units_dict[client_tank_id]
    assert client_mirror.net_disconnected is True, "client's mirrored tank should show the disconnected flag from the snapshot"
    print("OK: disconnected flag propagates through a real snapshot to the client's mirrored tank")

    # Recovery: once fresh packets arrive again, the flag should clear
    host.network._last_seen[client_addr] = time.time()
    assert host.network.stale_client_ids() == set(), "client should no longer be flagged once packets resume"
    print("OK: disconnect flag clears once packets resume")

    # Symmetric client-side check: client loses the host
    assert client.network.host_connection_lost() is False, "should not report lost immediately after a fresh packet"
    client.network._last_host_packet_at -= (networking.DISCONNECT_TIMEOUT + 1)
    assert client.network.host_connection_lost() is True, "client should detect a silent host after the timeout"
    print("OK: client correctly detects a silent host via host_connection_lost()")

    host.network.stop()
    client.network.stop()
    print("\nALL DISCONNECT DETECTION CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
