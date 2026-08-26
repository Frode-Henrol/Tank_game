"""Regression test: starting a second multiplayer session (host + client rejoin after a previous
match fully ended) must not crash.

Real bug: Multiplayer.client_id_counter starts at 1 and increments on every JOIN, but was never
reset when a fresh hosting session began. After a first match ended (shut_down_socket() on both
sides, e.g. both players died), starting a new session and rejoining assigned the SAME client a
higher id (2, not 1) than the fresh match's player count supports - player_controlled_tank_num was
then used to index units_player_controlled (sized for the new match, e.g. 2 slots: 0 and 1), and
index 2 raised IndexError in draw_ammo_ui().

Critically, this reuses the SAME host/client TankGame (and thus the same long-lived Multiplayer
instance) across both "matches" - exactly how the real game behaves (the process doesn't restart
between matches, the user just navigates back to the lobby and re-hosts/re-joins). An earlier
version of this test created fresh objects for match 2, which always got a fresh client_id_counter
regardless of the fix and so passed even against the broken code - a false positive.

Run directly: `python tests/test_multiplayer_rejoin_after_match.py`
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

PORT = 7786


def wait_until(predicate, timeout=5.0, interval=0.005):
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


def main():
    host = fresh_game(hosting=True)
    client = fresh_game(joined=True)

    # ---- Match 1: connect, then end the session on both sides, exactly like a full wipe would ----
    host.network.start_host(username="Host", port=PORT)
    client.network.start_client(host_ip="127.0.0.1", username="Client", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected the first time"
    assert client.network.client_id == 1, f"expected the first joiner to get id 1, got {client.network.client_id}"

    host.shut_down_socket()
    client.shut_down_socket()
    print("OK: first match connected (client id 1) and both sides tore down cleanly")

    # ---- Match 2: SAME host/client objects (same long-lived Multiplayer instances) rejoin, exactly
    # what "both died, back to lobby, try another" does in the real game - the process never restarts. ----
    host.hosting_game = True
    client.joined_game = True
    host.network.start_host(username="Host", port=PORT)
    client.network.start_client(host_ip="127.0.0.1", username="Client", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected the second time"

    assert client.network.client_id == 1, (
        f"a fresh session must start client ids from 1 again, got {client.network.client_id} - "
        f"this is the actual bug: a stale counter (left over from match 1) handing out an id that "
        f"no longer fits the new match's units_player_controlled size"
    )
    print("OK: second session's client also got id 1 (counter correctly reset, not a stale higher value)")

    host.start_multiplayer_campaign()
    host.playthrough([])  # bootstrap: loads level 1

    assert wait_until(lambda: len(host.units_player_controlled) == 2), "host never spawned 2 player slots"
    client.player_controlled_tank_num = client.network.client_id
    # This is exactly the line that crashed with IndexError in draw_ammo_ui() before the fix.
    assert 0 <= client.player_controlled_tank_num < len(host.units_player_controlled), (
        f"player_controlled_tank_num {client.player_controlled_tank_num} is out of range for "
        f"units_player_controlled (len {len(host.units_player_controlled)}) - this is the IndexError"
    )
    print("OK: rejoining client's player_controlled_tank_num correctly indexes the new match's player list")

    host.network.stop()
    client.network.stop()
    print("\nALL REJOIN-AFTER-MATCH CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
