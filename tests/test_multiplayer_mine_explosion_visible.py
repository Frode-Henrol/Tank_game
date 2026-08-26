"""Regression test: a client must actually see a mine's explosion (animation + sound trigger), not
just watch it silently vanish from the map.

Real bug found from live testing ("mines don't use the correct explosion size" - turned out to mean
the client's explosion looked wrong/missing compared to the host's, not a radius value mismatch).

Root cause: tankgame.py's host-side mine handling removed an exploded mine from self.mines in the
very same update() tick it exploded in (Mine.explode() sets is_exploded=True; the very next lines,
same tick, called self.mines.remove(mine)). host_broadcast_snapshot() always runs strictly after
update() finishes for a tick, so it could only ever see self.mines *after* removal - the mine had
already vanished from the authoritative list before any snapshot describing it as exploded=True
could go out. Clients never received an exploded=True transition for any mine, so
client_apply_snapshot()'s "was_exploded=False -> is_exploded=True" edge-trigger check (which drives
handle_mine_explosion() client-side) could never fire - the mine just disappeared from the client's
mine list with no explosion shown at all, while the host's own screen (which triggers its explosion
locally, immediately, same tick) showed the real thing.

Also fixed as part of the same change: the old removal loop was nested inside the per-unit loop
(iterating once per alive unit for no reason) and mutated self.mines with .remove() while iterating
it directly - a list-mutation-during-iteration bug matching the one already fixed for
Mine.explode()'s own obstacle-destruction loop.

The fix: an exploded mine now lingers in self.mines for a short delay (Mine.ready_for_cleanup())
after exploding, guaranteeing it's included in several outgoing snapshots before being removed - the
client's existing edge-trigger logic then works exactly as originally intended, no client-side
changes needed.

Run directly: `python tests/test_multiplayer_mine_explosion_visible.py`
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
from tankgame.object_classes.mine import Mine  # noqa: E402

MULTIPLAYER_MAP = os.path.join(REPO_ROOT, "tankgame", "map_files", "multiplayer_test.txt")
PORT = 7801


def wait_until(predicate, timeout=2.0, interval=0.002):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


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


def main():
    host = fresh_multiplayer_game()
    client = fresh_multiplayer_game()

    host.network.start_host(username="Host", port=PORT)
    client.network.start_client(host_ip="127.0.0.1", username="Client", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected"

    # Place a mine that's already primed to explode this tick (owned by nobody, so it doesn't kill
    # the tanks used for other assertions - the explosion mechanics themselves aren't what's under test).
    mine = Mine(image=None, spawn_point=(400, 400), explode_radius=100, owner_id=-1, team=99)
    mine.unit_list = []
    mine.obstacles_des = []
    host.mines = [mine]

    mine.explode()
    assert mine.is_exploded is True
    assert len(host.active_mine_explosions) == 0, "sanity check: hasn't been handled yet"

    # One host tick: explosion handling should fire (host's own screen sees it immediately, as before),
    # but the mine must NOT be removed from self.mines yet - it needs to survive into the snapshot.
    host.update()
    assert len(host.active_mine_explosions) == 1, "host's own explosion animation should trigger immediately"
    assert mine in host.mines, (
        "the mine was removed from self.mines in the same tick it exploded - this is the actual bug: "
        "host_broadcast_snapshot() (which always runs after update() finishes) can only ever see "
        "self.mines *after* this point, so it would never be able to describe this mine as "
        "exploded=True to a client"
    )
    print("OK: host's own explosion plays immediately, and the mine survives past this tick's update()")

    prev_snapshot = client.network.snapshot_from_host
    host.host_broadcast_snapshot()
    assert wait_until(lambda: client.network.snapshot_from_host is not prev_snapshot), \
        "client never received a snapshot"

    snapshot_mines = client.network.snapshot_from_host.get("mines", [])
    assert any(m["id"] == mine.id and m["exploded"] for m in snapshot_mines), (
        f"the broadcast snapshot never described mine id={mine.id} as exploded=True - got {snapshot_mines}"
    )
    print("OK: the snapshot the client actually received describes the mine as exploded=True")

    assert len(client.active_mine_explosions) == 0, "sanity check: client hasn't applied the snapshot yet"
    client.client_apply_snapshot()
    assert len(client.active_mine_explosions) == 1, (
        "client received exploded=True but never triggered its own explosion animation - "
        "client_apply_snapshot()'s edge-trigger check failed to fire"
    )
    print("OK: client correctly triggered its own explosion animation from the snapshot")

    # Eventually (once ready_for_cleanup() is true), the mine must still actually be removed - this
    # isn't a permanent leak, just a deliberate short delay.
    for _ in range(200):
        host.update()
        if mine not in host.mines:
            break
    assert mine not in host.mines, "the exploded mine was never cleaned up from self.mines at all"
    print("OK: the mine is eventually cleaned up from self.mines after the linger delay")

    host.network.stop()
    client.network.stop()
    print("\nALL MINE EXPLOSION VISIBILITY CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
