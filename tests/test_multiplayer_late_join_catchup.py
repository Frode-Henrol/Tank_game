"""Regression test for the actual bug found via real-world testing: a client that hasn't finished
joining yet when the host clicks "Start Game" would wait in the lobby forever, because the message
that moves it out of the lobby (level_result) was a one-shot send with no retry - unlike the JOIN
handshake (which does retry) or snapshots (continuously re-sent). This is a real, easy-to-hit race
that requires no packet loss at all, just ordinary timing between "host starts" and "client joins".

The fix: the host periodically re-sends its latest level_result (piggybacking on the existing
"clients" list broadcast cadence), and the client tracks the highest sequence number it's already
applied so a repeat resend is safely ignored instead of disrupting an already-caught-up client.

This test also covers the idempotency guard directly: applying the same payload twice must not
re-trigger a level reload or state change on the second application.

Run directly: `python tests/test_multiplayer_late_join_catchup.py`
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

PORT = 7787


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
    game.delta_time = game.fixed_delta_time_step
    return game


def main():
    # ---- Part 1: the actual race - host starts the campaign BEFORE any client has joined ----
    host = fresh_game(hosting=True)
    host.network.start_host(username="Host", port=PORT)

    host.campaign_start_grace_period = 0  # skip the real-time grace delay - not what this test covers
    host.start_multiplayer_campaign()
    host.multiplayer_run_lobby()  # elapses the (zeroed) grace period, actually flips state to PLAYTHROUGH
    host.playthrough([])  # bootstrap: broadcasts outcome="start" to clients_meta, which is EMPTY right now
    assert host.state == States.INFO_SCREEN
    assert len(host.network.clients_meta) == 0, "sanity check: nobody has joined yet"
    print("OK: host started the campaign with zero clients connected (the original one-shot send reaches nobody)")

    # Now a client joins, well after that one-shot send already went out to nobody
    client = fresh_game(joined=True)
    client.network.start_client(host_ip="127.0.0.1", username="LateClient", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected"
    client.player_controlled_tank_num = client.network.client_id
    print("OK: client connected after the host had already started")

    # Simulate the real main loop calling ONLY multiplayer_run_lobby() every tick on both sides -
    # deliberately not calling client_handle_level_result() directly, since that's exactly what let
    # the real bug slip through every other test: client_handle_level_result() actually getting the
    # client out of the lobby depends entirely on multiplayer_run_lobby() calling it internally
    # (it must - playing()'s tick loop, where it used to live, only runs once state is already
    # PLAYING, which is circular). This must exercise the real wiring, not the function in isolation.
    deadline = time.time() + 5.0
    caught_up = False
    while time.time() < deadline:
        host.multiplayer_run_lobby()
        client.multiplayer_run_lobby()
        if client.current_level_number == 1 and client.state == States.INFO_SCREEN:
            caught_up = True
            break
        time.sleep(0.01)

    assert caught_up, "client never caught up via the periodic level_result resend - this is the actual bug"
    assert sorted(u.id for u in client.units) == sorted(u.id for u in host.units)
    print("OK: late-joining client caught up to the already-started campaign via the periodic resend")

    host.network.stop()
    client.network.stop()

    # ---- Part 2: idempotency - applying the same payload twice must be a no-op the second time ----
    solo = fresh_game(hosting=True)
    solo.hosting_game = True  # host role, but we drive it directly without real sockets for this part
    solo.start_multiplayer_campaign()
    solo._broadcast_level_result("start")  # builds and caches a real payload with seq=1 (host_to_clients_send is a no-op with no clients)
    payload = solo._last_level_result_payload
    assert payload is not None and payload["seq"] == 1

    receiver = fresh_game(joined=True)
    receiver.network.level_result = payload
    receiver.client_handle_level_result()
    first_level = receiver.current_level_number
    first_state = receiver.state
    assert receiver._client_applied_level_result_seq == 1

    # Mutate what a naive re-apply would clobber, then feed the SAME payload again
    receiver.state = States.PLAYING
    receiver.network.level_result = payload
    receiver.client_handle_level_result()

    assert receiver.state == States.PLAYING, "a repeat of an already-applied level_result must not change state again"
    assert receiver.current_level_number == first_level
    print("OK: re-applying the same level_result payload is a safe no-op (idempotency guard works)")

    print("\nALL LATE-JOIN CATCHUP CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
