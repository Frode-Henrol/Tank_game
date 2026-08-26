"""Regression test: exiting to the main menu (pause menu, "Main menu") mid-multiplayer-match must
actually close the socket.

Before the fix, pause_menu_buttons' "Main menu" button had no action at all - it just jumped
straight to States.MENU, leaving hosting_game/joined_game True and the socket bound. A later
"Start Host" attempt on the same port then failed with OSError 10048 ("Only one usage of each
socket address is normally permitted"), since the old socket was never closed.

Run directly: `python tests/test_multiplayer_exit_to_menu.py`
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import tankgame  # noqa: E402
sys.path.insert(0, os.path.join(REPO_ROOT, "tankgame"))

from tankgame.tankgame import TankGame, States  # noqa: E402
from tankgame.object_classes.tank import Tank  # noqa: E402
from tankgame.object_classes.obstacle import Obstacle  # noqa: E402

PORT = 7793


def main():
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game = TankGame()

    # Host, start a campaign, get mid-match
    game.hosting_game = True
    game.network.start_host(username="Host", port=PORT)
    game.campaign_start_grace_period = 0  # skip the real-time grace delay - not what this test covers
    game.start_multiplayer_campaign()
    game.multiplayer_run_lobby()  # elapses the (zeroed) grace period, actually flips state to PLAYTHROUGH
    game.playthrough([])
    assert game.state == States.INFO_SCREEN
    assert game.playthrough_started is True

    # Exactly what the pause menu's "Main menu" button now does (ESC -> pause -> Main menu)
    game.state = States.PAUSE_MENU
    game.exit_to_main_menu()

    assert game.hosting_game is False, "hosting_game should be cleared"
    assert game.joined_game is False, "joined_game should be cleared"
    assert game.network.running is False, "the network object should report stopped"
    assert game.playthrough_started is False, "playthrough state should also reset, like main_menu()'s own cleanup"
    print("OK: exit_to_main_menu() clears hosting_game/joined_game/playthrough_started and stops the network")

    # The real regression check: a fresh host must be able to bind the exact same port afterward.
    # Before the fix this raised OSError 10048 (address already in use) because the old socket,
    # bound by `game` above, was never closed.
    Tank._id_counter = 0
    Obstacle._id_counter = 0
    game2 = TankGame()
    game2.hosting_game = True
    game2.network.start_host(username="Host2", port=PORT)  # raises OSError if the old socket leaked
    print("OK: re-hosting on the same port succeeded - the old socket was actually closed")

    game2.network.stop()
    print("\nALL EXIT-TO-MENU SOCKET CLEANUP CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
