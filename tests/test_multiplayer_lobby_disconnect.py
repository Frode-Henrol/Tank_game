"""Regression test: a client that disconnects while still in the lobby (before Start Game) must
stop showing up in the host's player list.

Before this fix, Multiplayer.clients_meta was never pruned (the only cleanup path,
_handle_client_disconnect, was dead code with its sole call site commented out) - once a client
joined, its name stayed in the lobby forever even after the client process closed.

The fix adds a lobby heartbeat (a joined client with nothing else to send pings the host once a
second) and host-side pruning of clients that have gone quiet for DISCONNECT_TIMEOUT, applied only
while still in the lobby (not mid-game, where a silent client should stay visually flagged instead
of vanishing - see test_multiplayer_disconnect.py for that path).

Run directly: `python tests/test_multiplayer_lobby_disconnect.py`
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

import tankgame.utils.networking as networking  # noqa: E402
from tankgame.tankgame import TankGame  # noqa: E402
from tankgame.object_classes.tank import Tank  # noqa: E402
from tankgame.object_classes.obstacle import Obstacle  # noqa: E402

PORT = 7792


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
    return game


def lobby_player_names(host):
    names = [v["username"] for v in host.network.clients_meta.values()]
    names.insert(0, "HOST BRIAN")
    return names


def main():
    host = fresh_game(hosting=True)
    client = fresh_game(joined=True)
    assert host.playthrough_started is False

    host.network.start_host(username="Host", port=PORT)
    client.network.start_client(host_ip="127.0.0.1", username="LobbyClient", port=PORT)
    assert wait_until(lambda: client.network.client_id != 0), "client never connected"
    addr = next(iter(host.network.clients_meta.keys()))

    assert "LobbyClient" in lobby_player_names(host)
    print("OK: connected client shows up in the host's lobby player list")

    # A connected client idling in the lobby must not get pruned - the heartbeat should keep
    # refreshing _last_seen even though there's no gameplay input yet.
    client.network.send_lobby_heartbeat()
    assert wait_until(lambda: addr in host.network._last_seen), "heartbeat never reached the host"
    host.network.prune_stale_clients()
    assert "LobbyClient" in lobby_player_names(host), "an actively-connected client must not be pruned"
    print("OK: a live client sending heartbeats is never pruned from the lobby")

    # Simulate the client vanishing (closed the window, crashed, lost connection) - no more
    # heartbeats arrive. Backdate rather than actually waiting DISCONNECT_TIMEOUT+ seconds.
    host.network._last_seen[addr] -= (networking.DISCONNECT_TIMEOUT + 1)
    host.network.prune_stale_clients()

    assert addr not in host.network.clients_meta, "stale client should have been pruned from clients_meta"
    assert "LobbyClient" not in lobby_player_names(host), "disconnected client's name must disappear from the lobby list"
    print("OK: a client that goes silent in the lobby is pruned and disappears from the player list")

    host.network.stop()
    client.network.stop()
    print("\nALL LOBBY DISCONNECT CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
