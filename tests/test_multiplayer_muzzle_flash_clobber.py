"""Regression test: a tank's muzzle flash animation must not be silently skipped when two shots'
worth of snapshot updates land within the same rendered frame.

Real bug found from live testing: client_apply_snapshot() runs once per fixed-timestep sim tick
(playing()'s "while accumulator >= delta_time" loop), and that loop can run several ticks before a
single draw() call - simulation ticks can outrun renders. If two consecutive snapshots both show an
incremented shot_counter for the same tank within that window (an ordinary double-shot, nothing
exotic), the old code unconditionally replaced unit.muzzle_flash_animation with a brand new
Animation object on the second trigger - resetting it to frame 0 before draw() ever rendered the
first one even once. The first muzzle flash silently never appeared on screen. This matches what
was reported as "sometimes the client can't see the gunsmoke animation from tanks".

The fix: only start a new Animation if the tank doesn't already have one in flight (None or
finished). The already-playing animation is left alone to finish instead of being clobbered.

Run directly: `python tests/test_multiplayer_muzzle_flash_clobber.py`
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import tankgame  # noqa: E402
sys.path.insert(0, os.path.join(REPO_ROOT, "tankgame"))

from tankgame.tankgame import TankGame  # noqa: E402
from tankgame.object_classes.tank import Tank  # noqa: E402
from tankgame.object_classes.obstacle import Obstacle  # noqa: E402

MULTIPLAYER_MAP = os.path.join(REPO_ROOT, "tankgame", "map_files", "multiplayer_test.txt")


def fresh_multiplayer_game():
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game = TankGame()
    game.clear_all_map_data()
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game.load_map(MULTIPLAYER_MAP)
    game.load_map_textures()
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
    client = fresh_multiplayer_game()
    unit = client.units_player_controlled[0]
    assert "muzzle_flash" in unit.animations, "sanity check: this unit has muzzle flash frames loaded"

    # First shot's snapshot arrives and is applied - starts a fresh animation.
    client.network.snapshot_from_host = snapshot_for(unit, shot_counter=1)
    client.client_apply_snapshot()
    assert unit.muzzle_flash_animation is not None, "first shot should start a muzzle flash animation"
    first_animation = unit.muzzle_flash_animation
    assert first_animation.finished is False
    print("OK: first shot started a muzzle flash animation")

    # A second shot's snapshot lands and is applied in the SAME rendered frame (no draw() call, and
    # therefore no Animation.play() call, happened in between) - simulating two sim ticks outrunning
    # one render. The still-in-flight animation from the first shot must not be replaced.
    client.network.snapshot_from_host = snapshot_for(unit, shot_counter=2)
    client.client_apply_snapshot()
    assert unit.muzzle_flash_animation is first_animation, (
        "the first shot's animation was replaced with a new one before it ever got a chance to "
        "render a single frame - this is the actual bug: the first muzzle flash silently never appears"
    )
    print("OK: second same-frame shot did not clobber the first shot's still-playing animation")

    # Once the first animation actually finishes (drawn out via play(), like the real render loop
    # does every frame), a subsequent shot must be free to start a new one.
    dummy_surface = client.screen
    while not first_animation.finished:
        first_animation.play(dummy_surface)
    client.network.snapshot_from_host = snapshot_for(unit, shot_counter=3)
    client.client_apply_snapshot()
    assert unit.muzzle_flash_animation is not None and unit.muzzle_flash_animation is not first_animation, \
        "a new shot after the previous animation finished should start a fresh animation"
    print("OK: a new animation starts normally once the previous one has actually finished playing")

    print("\nALL MUZZLE-FLASH CLOBBER CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
