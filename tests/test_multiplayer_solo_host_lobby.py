"""Regression test: a host sitting alone in the lobby (no client has joined yet) must not crash.

multiplayer_run_lobby() throttles the "clients" name-list network broadcast to once a second, but a
prior version of that throttle accidentally made the *local* all_player_names variable only get
assigned inside the throttled branch - so on any frame that wasn't a broadcast frame, the later
`if all_player_names:` check raised UnboundLocalError. Every existing multiplayer test immediately
connects a client, so none of them exercised this - the most common real state when a host first
opens the lobby (waiting, no one connected yet).

Run directly: `python tests/test_multiplayer_solo_host_lobby.py`
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

PORT = 7789


def main():
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game = TankGame()
    game.hosting_game = True
    game.network.start_host(username="Host", port=PORT)

    # Many calls, spanning multiple throttle windows, with nobody ever joining - the exact
    # scenario that crashed before: "Start Host" then just sitting in the lobby.
    for i in range(50):
        game.multiplayer_run_lobby()

    assert game.player1_button.text == "HOST BRIAN", f"expected host's own name shown, got {game.player1_button.text!r}"
    print("OK: solo host in the lobby survives repeated multiplayer_run_lobby() calls with no client, no crash")

    game.network.stop()
    print("\nALL SOLO HOST LOBBY CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
