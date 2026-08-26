"""Regression test: a muzzle flash animation that has already rendered at least one frame must be
free to restart for a new shot - it must not have to play out to completion first.

Real bug: the fix in test_multiplayer_muzzle_flash_clobber.py (guard against replacing an animation
that hasn't rendered any frames yet) was originally written as "only replace once the current
animation has fully finished" (gated on Animation.finished). That over-corrected: a full muzzle
flash animation can take the better part of a real second to play out (15 frames at frame_delay=2),
so under any reasonably sustained fire rate, most shots landed while the previous animation was
still mid-playback. Each one got folded into _client_last_shot_counter's "already seen" watermark
without ever starting its own animation - once folded in, that shot could never trigger a flash
later either, since the watermark had already moved past it. A stress simulation (real host firing
on a real cooldown, ~6 shots/second, snapshots applied at a realistic throttled rate) showed 352
actual shots fired producing only a handful of visible flashes with the .finished-gated version -
this is what "the client only sometimes shows a muzzle flash" turned out to actually be, and it's
also why bullet explosions never had this problem: each projectile is its own independent object,
not a single shared per-tank animation slot that has to fully finish before it can be reused.

The fix: gate on Animation.rendered_at_least_once instead of Animation.finished - a new shot can
freely restart the flash as soon as the current one has been drawn even once (closing the original
same-tick race, which only needs about one render frame's worth of protection), instead of having to
wait for the whole animation to play out.

Run directly: `python tests/test_multiplayer_muzzle_flash_starvation.py`
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
    assert len(unit.animations["muzzle_flash"]) > 3, "sanity check: this animation has multiple frames"

    # First shot starts an animation.
    client.network.snapshot_from_host = snapshot_for(unit, shot_counter=1)
    client.client_apply_snapshot()
    first_animation = unit.muzzle_flash_animation
    assert first_animation is not None

    # Render exactly one frame - enough to prove it was actually shown, nowhere near enough frames
    # to finish the whole animation (frame_delay=2, several images long).
    first_animation.play(client.screen)
    assert first_animation.rendered_at_least_once is True
    assert first_animation.finished is False, "sanity check: nowhere near finished after one play() call"
    print("OK: first shot's animation has rendered exactly one frame and is far from finished")

    # A second shot lands well before the first animation has played out. It must still get its own
    # fresh flash - a real tank firing every ~150-300ms (a normal cooldown) fires far more often than
    # once per ~1 real second (roughly how long the full animation takes to play out), so requiring
    # "fully finished" before allowing a restart would starve nearly every shot during sustained fire.
    client.network.snapshot_from_host = snapshot_for(unit, shot_counter=2)
    client.client_apply_snapshot()
    assert unit.muzzle_flash_animation is not first_animation, (
        "the second shot's flash was suppressed because the first animation hadn't fully finished "
        "yet - this is the actual bug: gating the restart on Animation.finished (instead of having "
        "rendered at least one frame) starves the flash under any sustained fire rate, since a full "
        "animation can take far longer to finish than the real gap between shots"
    )
    print("OK: second shot restarted the flash fresh, without waiting for the first animation to finish")

    print("\nALL MUZZLE-FLASH STARVATION CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
