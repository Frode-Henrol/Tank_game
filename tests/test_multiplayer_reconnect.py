"""Regression test: stopping and immediately restarting a Multiplayer session (e.g. "Back" then
"Join Game" again) must not leave two receive threads sharing the same socket.

Before this fix, start_host()/start_client() didn't track their thread, so stop() couldn't wait for
it to actually exit - a fast enough restart could start a new thread before the old one had finished
unwinding from its closed socket, and since both read self.socket dynamically (not a captured
reference), they'd both end up reading the new socket concurrently.

Run directly: `python tests/test_multiplayer_reconnect.py`
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

PORT = 7791


def wait_until(predicate, timeout=2.0, interval=0.002):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def main():
    net = networking.Multiplayer()
    net.start_host(username="Host", port=PORT)
    first_thread = net._thread
    assert first_thread is not None and first_thread.is_alive()

    net.stop()
    assert not first_thread.is_alive(), "stop() must not return until the old recv thread has actually exited"
    print("OK: stop() waits for the recv thread to fully exit before returning")

    # Immediately restart, same object - exactly what "Back" then "Start Host" again does in the UI
    net.start_host(username="Host", port=PORT)
    second_thread = net._thread
    assert second_thread is not first_thread, "restarting must spin up a fresh thread"
    assert second_thread.is_alive()
    print("OK: restarting after stop() gets a clean new thread, no overlap with the old one")

    # Prove it's not just alive but actually usable: a real client can connect through it
    client = networking.Multiplayer()
    client.start_client(host_ip="127.0.0.1", username="Client", port=PORT)
    assert wait_until(lambda: client.client_id != 0), "client failed to connect to the restarted host"
    print("OK: the restarted host socket is fully functional - a client connected through it")

    net.stop()
    client.stop()
    print("\nALL RECONNECT CHECKS PASSED")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
