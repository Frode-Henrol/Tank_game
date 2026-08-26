"""Regression test: laying a mine must still work after the game has been running for a while, not
just on the very first tick.

Real bug introduced while fixing mine explosion visibility (see test_multiplayer_mine_explosion_visible.py):
update()'s mine cleanup step rebound self.mines to a brand new list object every single tick
(`self.mines = [mine for mine in self.mines if not mine.ready_for_cleanup()]`), unconditionally, even
when there was nothing to clean up. But Tank.global_mine_list (set once at map load time, in
load_map()) holds a reference to the *original* list object - a tank's lay_mine() appends newly-laid
mines to that reference. Rebinding self.mines to a new list object on literally the very first tick
silently broke that reference forever: TankGame.mines pointed to a fresh list from then on, while
every tank's global_mine_list still pointed at the old, now-abandoned one. Every mine laid after the
first tick got appended to a list nothing ever reads again - mines appeared to stop being deployable
at all (this reproduces after ~1 tick, so it hit basically immediately in real play).

The fix: mutate self.mines in place (slice assignment, self.mines[:] = ...) instead of rebinding.

Run directly: `python tests/test_mine_deploy_after_ticks.py`
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


def main():
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game = TankGame()
    game.clear_all_map_data()
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game.load_map()
    game.load_map_textures()
    game.delta_time = game.fixed_delta_time_step

    original_mines_list_id = id(game.mines)

    player = game.units_player_controlled[0]
    assert player.mine_limit > 0, "sanity check: this tank can actually lay mines"

    # Simulate ~3 real seconds of normal gameplay ticks (well past lay_mine()'s own 2-second grace
    # period) with nobody laying a mine yet - just running update() over and over, since the bug
    # doesn't need an actual mine to exist, only for update()'s cleanup step to run.
    for _ in range(300):
        game.update()

    assert id(game.mines) == original_mines_list_id, (
        "self.mines was rebound to a new list object during normal ticking - this is the actual bug: "
        "Tank.global_mine_list (bound once at map load) would now be pointing at an abandoned list "
        "that TankGame never reads from again"
    )
    print("OK: self.mines is still the same list object after 300 ticks of normal play")

    assert player.time_alive >= 2, "sanity check: enough time has passed for lay_mine()'s grace period"
    player.lay_mine()

    assert len(game.mines) == 1, (
        f"lay_mine() was called but the mine never showed up in game.mines (got {len(game.mines)} "
        f"mines) - it was appended to Tank.global_mine_list, which no longer matches game.mines"
    )
    print("OK: a mine laid after 3 seconds of play actually shows up in game.mines")

    print("\nALL MINE-DEPLOY-AFTER-TICKS CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
