"""Regression test: a client must see muzzle flash / hear cannon fire again immediately after a
level transition, even though the new level's tanks reuse low ids from the previous level.

Real bug found from live testing ("client sometimes can't see the gunsmoke animation"):
_client_last_shot_counter is keyed by tank id, and clear_all_map_data() resets Tank._id_counter to
0 on every level transition - so a fresh level's tanks reuse the exact same low ids as the previous
level's tanks (id 0, 1, 2... again). The dict was only ever cleared on full session teardown
(shut_down_socket()), never on a level transition. So a brand new Tank object in the new level,
reusing an old id, inherited the *previous* level's shot_fired_counter high-water mark from the dict
- its first several shots in the new level (until its own fresh counter organically climbed back
past that stale watermark) silently failed the "shot_counter > last seen" edge-trigger check: no
muzzle flash, no cannon sound. This reproduced on literally every level transition, not just rare
timing - a much bigger contributor to "sometimes missing" than the same-frame clobber bug fixed
earlier (see test_multiplayer_muzzle_flash_clobber.py).

Run directly: `python tests/test_multiplayer_shot_counter_level_reset.py`
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

PORT = 7800


def wait_until(predicate, timeout=5.0, interval=0.002):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def apply_level_result_until(client, condition, timeout=5.0, interval=0.005):
    deadline = time.time() + timeout
    while time.time() < deadline:
        client.multiplayer_run_lobby()
        if condition():
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


def snapshot_for(unit, shot_counter):
    return {
        "tanks": [{
            "id": unit.id,
            "x": unit.pos[0],
            "y": unit.pos[1],
            "degrees": unit.degrees,
            "turret": unit.turret_rotation_angle,
            "dead": False,
            "shot_counter": shot_counter,
        }],
        "projectiles": [],
        "mines": [],
    }


def main():
    host = fresh_game(hosting=True)
    client = fresh_game(joined=True)

    host.network.start_host(username="Host", port=PORT)
    client.network.start_client(host_ip="127.0.0.1", username="Client", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected"
    client.player_controlled_tank_num = client.network.client_id

    host.campaign_start_grace_period = 0  # skip the real-time grace delay - not what this test covers
    host.start_multiplayer_campaign()
    host.multiplayer_run_lobby()  # elapses the (zeroed) grace period, actually flips state to PLAYTHROUGH
    host.playthrough([])  # bootstrap branch: loads level 1

    assert apply_level_result_until(client, lambda: client.current_level_number == 1 and client.state == States.INFO_SCREEN), \
        "client never caught up to the start level_result"

    # A tank on the client (matches whatever id level 1 assigned it - the point of the test is this
    # exact id gets reused next level) racks up several shots during level 1.
    level1_unit = client.units[0]
    level1_id = level1_unit.id
    client.network.snapshot_from_host = snapshot_for(level1_unit, shot_counter=5)
    client.client_apply_snapshot()
    assert client._client_last_shot_counter[level1_id] == 5
    print(f"OK: level 1 tank id={level1_id} fired 5 shots (high-water mark recorded)")

    # ---- Level clear: host advances to level 2, ids reset (clear_all_map_data() -> Tank._id_counter = 0) ----
    player_team = host.units_player_controlled[0].team
    for unit in host.units:
        if unit.team != player_team:
            unit.dead = True
    host.state = States.PLAYTHROUGH
    host.playthrough([])  # win branch: advances to level 2, broadcasts outcome="level_complete"
    assert host.current_level_number == 2

    assert apply_level_result_until(client, lambda: client.current_level_number == 2), \
        "client never caught up to the level_complete result"

    level2_unit = client.units[0]
    assert level2_unit.id == level1_id, (
        f"sanity check: level 2's first tank should reuse id {level1_id} (Tank._id_counter resets "
        f"every level) - got {level2_unit.id} instead, the premise of this test doesn't hold"
    )
    assert level2_unit is not level1_unit, "sanity check: this must be a brand new Tank instance"
    print(f"OK: level 2's tank reused the same id ({level1_id}) as a fresh object, as expected")

    # This brand new tank's very first shot in level 2 (shot_counter=1) must still trigger a muzzle
    # flash, despite _client_last_shot_counter[level1_id] having been left at 5 from level 1.
    client.network.snapshot_from_host = snapshot_for(level2_unit, shot_counter=1)
    client.client_apply_snapshot()
    assert level2_unit.muzzle_flash_animation is not None, (
        "level 2's tank fired its first shot but no muzzle flash was triggered - this is the actual "
        "bug: a stale shot_counter high-water mark left over from the previous level (which used the "
        "same reused tank id) suppressed it"
    )
    print("OK: level 2's tank's first shot correctly triggered a muzzle flash - stale watermark cleared")

    host.network.stop()
    client.network.stop()
    print("\nALL SHOT-COUNTER LEVEL-RESET CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
