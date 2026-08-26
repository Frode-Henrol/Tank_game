"""Regression test: a client whose JOIN is still in flight when the host clicks "Start Game" must
still be counted as a player - not silently spawn as a solo game.

Real bug found from live testing: multiplayer_player_count used to be computed synchronously,
inside start_multiplayer_campaign(), as `1 + len(clients_meta)` at the exact instant "Start Game"
was clicked. That count gets baked into the whole match (used once to inject player spawns into
the level, and never recomputed) - so a client whose JOIN handshake hadn't landed on the host yet
at that exact instant (very plausible right after a match ends, when both players are quickly
re-hosting/re-joining through several menu screens) got permanently left out: the host would spawn
with player_count=1, no second tank ever injected, on either side. To the rejoining player this
looked exactly like their tank had "disappeared" - it was simply never spawned.

The fix: start_multiplayer_campaign() no longer bootstraps synchronously. It arms a short grace
period (campaign_start_grace_period); multiplayer_run_lobby() (already running every frame while
hosting) only locks in the player count and flips state to PLAYTHROUGH once that period elapses -
giving a JOIN that's already in flight time to land first.

Run directly: `python tests/test_multiplayer_campaign_start_race.py`
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

from tankgame.tankgame import TankGame, States  # noqa: E402
from tankgame.object_classes.tank import Tank  # noqa: E402
from tankgame.object_classes.obstacle import Obstacle  # noqa: E402

PORT = 7799
GRACE_PERIOD = 0.5  # short but real, so the test stays fast while still exercising actual elapsed time


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
    host.network.start_host(username="Host", port=PORT)
    host.campaign_start_grace_period = GRACE_PERIOD

    # Host clicks "Start Game" with nobody connected yet.
    host.start_multiplayer_campaign()
    assert host.state != States.PLAYTHROUGH, (
        "start_multiplayer_campaign() must NOT bootstrap synchronously - it should only arm the "
        "grace period and let multiplayer_run_lobby() do the actual transition once it elapses"
    )
    print("OK: clicking Start Game does not immediately bootstrap the match")

    # A client's JOIN lands shortly after - well within the grace window, exactly like a rejoining
    # client whose handshake was still in flight when the host clicked Start.
    client = fresh_game(joined=True)
    client.network.start_client(host_ip="127.0.0.1", username="Client", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected"
    print("OK: client joined during the grace window")

    # Drive the host's lobby loop (like the real main loop does every frame) until the grace period
    # elapses and the campaign actually bootstraps.
    assert wait_until(lambda: (host.multiplayer_run_lobby(), host.state == States.PLAYTHROUGH)[1],
                       timeout=GRACE_PERIOD + 3.0), \
        "campaign never bootstrapped after the grace period should have elapsed"

    assert host.multiplayer_player_count == 2, (
        f"expected the client (joined mid-grace-period) to be counted, got "
        f"multiplayer_player_count={host.multiplayer_player_count} - this is the actual bug: a "
        f"too-early player count computed before the client's JOIN had landed"
    )
    print("OK: host correctly counted the late-arriving client (multiplayer_player_count == 2)")

    host.playthrough([])  # bootstrap branch: loads level 1 using the (correct) player count
    assert len(host.units_player_controlled) == 2, "level 1 should have spawned both player tanks"
    print("OK: both player tanks were actually spawned - the rejoining client's tank did not disappear")

    host.network.stop()
    client.network.stop()
    print("\nALL CAMPAIGN-START RACE CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
