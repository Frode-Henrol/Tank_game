"""Automated test for the campaign/lives sync between host and client.

Drives the real host_game_button-equivalent setup, start_multiplayer_campaign(), playthrough(),
_broadcast_level_result(), and client_handle_level_result() over real UDP sockets, and asserts the
client mirrors the host's level/lives decisions correctly for both outcomes: a level clear (advance
to the next level, fresh tank ids on both sides) and a full wipe (playthrough_lives hits 0 - one
life per level, no retries).

This deliberately skips the real info_screen()/count_down() blocking animations (fixed-duration
full-screen loops, not part of the sync logic) by driving state transitions directly instead of
through pg.time-based timers - it exercises the actual decision/sync methods, not the cosmetic
transition screens single-player already covers unmodified.

Run directly: `python tests/test_multiplayer_campaign.py`
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

from tankgame.tankgame import TankGame, States  # noqa: E402
from tankgame.object_classes.tank import Tank  # noqa: E402
from tankgame.object_classes.obstacle import Obstacle  # noqa: E402

PORT = 7797


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
    game.delta_time = game.fixed_delta_time_step
    return game


def main():
    host = fresh_game(hosting=True)
    client = fresh_game(joined=True)

    host.network.start_host(username="Host", port=PORT)
    client.network.start_client(host_ip="127.0.0.1", username="Client", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected"
    client.player_controlled_tank_num = client.network.client_id

    # ---- Start the campaign (host clicks "Start Game") ----
    host.start_multiplayer_campaign()
    assert host.playthrough_lives == 1, "multiplayer must pin lives to 1 (one life per level, no retries)"
    assert host.state == States.PLAYTHROUGH
    host.playthrough([])  # bootstrap branch: loads level 1, broadcasts outcome="start"

    assert host.state == States.INFO_SCREEN
    assert len(host.units_player_controlled) == 2, "level 1 should have a spawned/injected second player"
    host_ids = sorted(u.id for u in host.units)

    prev_result = client.network.level_result
    assert wait_until(lambda: client.network.level_result is not prev_result), "client never received the start level_result"
    client.client_handle_level_result()

    assert client.state == States.INFO_SCREEN
    assert client.current_level_number == host.current_level_number == 1
    assert sorted(u.id for u in client.units) == host_ids, "client's tank ids must match the host's after the campaign start"
    print("OK: campaign start synced - both sides on level 1 with matching tank ids")

    # Skip the (unmodified, single-player) info_screen/count_down blocking animations - jump both
    # sides straight to PLAYING, matching what those screens would do with playthrough_lives > 0.
    host.state = States.PLAYING
    client.state = States.PLAYING

    # ---- Outcome A: level clear ----
    player_team = host.units_player_controlled[0].team
    for unit in host.units:
        if unit.team != player_team:
            unit.dead = True

    host.state = States.PLAYTHROUGH
    host.playthrough([])  # win branch: advances to level 2, broadcasts outcome="level_complete"

    assert host.state == States.INFO_SCREEN
    assert host.current_level_number == 2
    host_ids_lvl2 = sorted(u.id for u in host.units)

    prev_result = client.network.level_result
    assert wait_until(lambda: client.network.level_result is not prev_result), "client never received the level_complete result"
    client.client_handle_level_result()

    assert client.current_level_number == 2
    assert sorted(u.id for u in client.units) == host_ids_lvl2
    assert len(client.units_player_controlled) == 2, "both players must be revived (present, non-dead) on the next level"
    assert not any(p.dead for p in client.units_player_controlled)
    print("OK: level clear synced - advanced to level 2, both players revived on both sides")

    host.state = States.PLAYING
    client.state = States.PLAYING

    # ---- Outcome B: full wipe -> immediate game over (no retry) ----
    for p in host.units_player_controlled:
        p.dead = True

    host.state = States.PLAYTHROUGH
    host.playthrough([])  # death branch: lives 1 -> 0, broadcasts outcome="died"

    assert host.playthrough_lives == 0, "one full wipe must exhaust the single life immediately"
    assert host.state == States.INFO_SCREEN

    prev_result = client.network.level_result
    assert wait_until(lambda: client.network.level_result is not prev_result), "client never received the died result"
    client.client_handle_level_result()

    assert client.playthrough_lives == 0
    print("OK: full wipe synced - playthrough_lives hit 0 on both sides (would trigger game-over in info_screen)")

    host.network.stop()
    client.network.stop()
    print("\nALL CAMPAIGN SYNC CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
