import socket
import threading
import time
import json
import traceback

DEFAULT_PORT = 7777
BUFFER_SIZE = 65535  # Max UDP payload; generous enough that a full world snapshot never gets silently truncated

CONNECT_RETRY_INTERVAL = 1.0  # seconds between resent JOIN requests while connecting
CONNECT_TIMEOUT = 8.0         # give up and report failure after this long with no response

DISCONNECT_TIMEOUT = 5.0  # a peer that's sent nothing in this long is considered disconnected
LOBBY_HEARTBEAT_INTERVAL = 1.0  # how often a connected client pings the host while idling in the lobby

class NetRole:
    """Enum for network roles."""
    NONE = 0
    HOST = 1
    CLIENT = 2

class Multiplayer:
    """Handles UDP-based multiplayer networking. Transport only - payloads are plain JSON-serializable dicts."""

    def __init__(self):
        """Initialize socket and role tracking."""
        self.socket = None
        self.running = False
        self.role = NetRole.NONE
        self.clients_meta = {}    # Meta data for clients
        self.client_list = []     # For client to store the list of connected clients' names

        self.server_address = None  # Client only

        self.snapshot_from_host = None    # Client: latest world-state dict received from host
        self.input_from_clients = {}      # Host: addr -> latest input dict received from that client
        self.level_result = None          # Client: one-shot campaign-transition message from host, consumed by caller

        self.client_id_counter = 1
        self.client_id = 0

        # Client-side connection handshake state (retry a lost JOIN/ID__ packet instead of hanging forever)
        self.connection_failed = False
        self._join_username = None
        self._connect_started_at = None
        self._last_join_sent_at = None
        self._join_attempts = 0

        # Disconnect detection (mid-game, after the join handshake is done)
        self._last_seen = {}         # Host: addr -> time.time() of the last packet received from that client
        self._last_host_packet_at = None  # Client: time.time() of the last packet received from the host
        self._last_heartbeat_sent_at = 0  # Client: time.time() of our last lobby heartbeat send

        self._thread = None  # the host/client recv thread, tracked so stop() can wait for it to actually exit


    def start_host(self, username, port=DEFAULT_PORT):
        """Start hosting a game on given port."""
        self.role = NetRole.HOST
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', port))
        self.running = True
        # Reset per-session client bookkeeping. client_id_counter in particular must start fresh -
        # it's used as the direct index into units_player_controlled (client_id 1 -> slot 1, etc, a
        # fixed-size list sized to the match's player count). Without this reset, a client rejoining
        # after a previous match ended gets an ever-higher id from a stale counter that no longer
        # fits the new match's (smaller) player list - an IndexError in draw_ammo_ui().
        self.client_id_counter = 1
        self.clients_meta.clear()
        self._thread = threading.Thread(target=self._host_loop, daemon=True)
        self._thread.start()
        print("Hosting started")

    def start_client(self, host_ip, username, port=DEFAULT_PORT):
        """Join a hosted game at host_ip:port."""
        self.role = NetRole.CLIENT
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Explicitly bind before the recv thread starts below. On Windows, an unbound UDP socket's
        # first recvfrom() can raise WSAEINVAL ("An invalid argument was supplied") if it runs before
        # anything has been sent yet (sendto() is what implicitly binds an unbound socket) - a real
        # race between this thread and the recv thread, since send_join_request() below is what would
        # otherwise do that implicit bind. Binding to an OS-assigned ephemeral port up front removes
        # the race entirely regardless of thread scheduling order.
        self.socket.bind(('', 0))
        self.server_address = (host_ip, port)
        self.running = True
        self.client_id = 0
        self.connection_failed = False
        self._join_username = username
        self._connect_started_at = time.time()
        self._last_join_sent_at = self._connect_started_at
        self._join_attempts = 0
        self._thread = threading.Thread(target=self._client_loop, daemon=True)
        self._thread.start()
        self.send_join_request(username)
        print("Client started")

    def retry_join_if_needed(self):
        """Call once per tick while joined_game is true. Resends the JOIN request until a client
        id arrives (recovers from a lost JOIN or ID__ packet on a lossy connection), and sets
        connection_failed after CONNECT_TIMEOUT seconds so the UI can show a clear failure instead
        of hanging forever - relevant over the internet, essentially never triggers on LAN/loopback."""
        if self.role != NetRole.CLIENT or self.client_id != 0 or self.connection_failed:
            return

        now = time.time()
        if now - self._connect_started_at >= CONNECT_TIMEOUT:
            self.connection_failed = True
            return

        if now - self._last_join_sent_at >= CONNECT_RETRY_INTERVAL:
            self._last_join_sent_at = now
            self.send_join_request(self._join_username)

    def stop(self):
        """Stop the socket and networking threads. Waits for the recv thread to actually exit before
        returning - otherwise a quick "Back, then try again" could start a new thread while the old
        one is still mid-shutdown, and since both read self.socket dynamically (not a captured
        reference), they'd end up racing to read the same new socket once it's reassigned."""
        self.running = False
        if self.socket:
            self.input_from_clients.clear()
            self.clients_meta.clear()
            self._last_seen.clear()
            self.socket.close()  # unblocks the thread's pending recvfrom() so it can see running=False
            print("Stopping socket")
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def send_join_request(self, username):
        """Send a join request to the server."""
        if self.role == NetRole.CLIENT:
            self._join_attempts += 1
            payload = username.encode()
            self.socket.sendto(b'JOIN' + payload, self.server_address)
            print(f"[DIAG] sent JOIN #{self._join_attempts} to {self.server_address} at {time.time():.2f} from local port {self.socket.getsockname()}")

    def connection_status_text(self):
        """Client-only: a human-readable status for the lobby UI while the join handshake is in
        progress or has failed - short enough to fit a lobby button, but distinguishes "the host has
        never sent us anything" from "the host has replied, just not with an id yet" so a one-way
        firewall block (host receives our JOIN, but its reply never arrives here) is diagnosable."""
        if self.role != NetRole.CLIENT or self.client_id != 0:
            return None

        ip, port = self.server_address
        if self.connection_failed:
            heard = "no reply ever" if self._last_host_packet_at is None else "host went quiet"
            return f"Failed: {ip}:{port} ({heard}) - check firewall on both PCs"

        elapsed = time.time() - self._connect_started_at
        heard = " - host seen!" if self._last_host_packet_at is not None else ""
        return f"Connecting {ip}:{port} #{self._join_attempts} {elapsed:.0f}s{heard}"

    def send_lobby_heartbeat(self):
        """Client-only: called every tick while joined_game is true. Once actually connected, a
        client sitting in the lobby has nothing else to send (client_send_input only starts once
        gameplay begins), so without this the host's last-seen timestamp for us would never refresh
        and prune_stale_clients() would (wrongly) drop us for being "silent" a few seconds after we
        successfully joined."""
        if self.role != NetRole.CLIENT or self.client_id == 0:
            return
        now = time.time()
        if now - self._last_heartbeat_sent_at >= LOBBY_HEARTBEAT_INTERVAL:
            self._last_heartbeat_sent_at = now
            self.client_to_host_send({"type": "heartbeat"})

    def prune_stale_clients(self):
        """Host-only, lobby use: removes clients_meta entries for clients who've gone silent for
        DISCONNECT_TIMEOUT (crashed, closed the window, lost their connection) so their name stops
        showing in the player list. Deliberately NOT used mid-game - there, a silent client should
        stay visually flagged (see host_broadcast_snapshot's "disconnected" tank flag) rather than
        vanish and free up their client_id/slot out from under an in-progress match."""
        for cid in self.stale_client_ids():
            # list(...) snapshots clients_meta before iterating - it's written from the recv thread
            # (a new JOIN) and read here from the main thread; iterating the live dict directly can
            # raise "dictionary changed size during iteration" if a join lands mid-loop.
            addr = next((a for a, meta in list(self.clients_meta.items()) if meta["id"] == cid), None)
            if addr is not None:
                self._handle_client_disconnect(addr)
                self._last_seen.pop(addr, None)
                self.input_from_clients.pop(addr, None)

    def client_to_host_send(self, payload: dict):
        """Send a JSON-serializable payload dict from client to host."""
        if self.role == NetRole.CLIENT:
            body = json.dumps(payload).encode()
            self.socket.sendto(b'DATA' + body, self.server_address)

    def host_to_clients_send(self, payload: dict):
        """Broadcast a JSON-serializable payload dict from host to all clients."""
        if self.role == NetRole.HOST:
            body = json.dumps(payload).encode()
            for client_addr in list(self.clients_meta.keys()):
                self.socket.sendto(b'DATA' + body, client_addr)

    def _handle_client_disconnect(self, addr):
        if addr in self.clients_meta:
            print(f"Removing disconnected client: {addr}")
            del self.clients_meta[addr]

    def _host_loop(self):
        """Receive and handle packets as host."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                if not data:
                    continue  # Empty data, keep listening

                self._handle_host_packet(data, addr)
            except ConnectionResetError:
                print(f"Client {addr} forcibly closed the connection")
                #self._handle_client_disconnect(addr)
                continue
            except Exception as e:
                print(f"Host error: {e}")
                continue



    def _client_loop(self):
        """Receive and handle packets as client."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                self._handle_client_packet(data, addr)
            except Exception:
                traceback.print_exc()

    def stale_client_ids(self):
        """Client ids (not addrs) whose most recent packet is older than DISCONNECT_TIMEOUT."""
        now = time.time()
        stale = set()
        # list(...) snapshots clients_meta before iterating - see prune_stale_clients() for why.
        for addr, meta in list(self.clients_meta.items()):
            last = self._last_seen.get(addr, meta["joined_at"])
            if now - last > DISCONNECT_TIMEOUT:
                stale.add(meta["id"])
        return stale

    def host_connection_lost(self):
        """Client-only: true once connected if nothing has arrived from the host in DISCONNECT_TIMEOUT."""
        if self.role != NetRole.CLIENT or self.client_id == 0 or self._last_host_packet_at is None:
            return False
        return time.time() - self._last_host_packet_at > DISCONNECT_TIMEOUT

    def _handle_host_packet(self, data, addr):
        """Process packets received by the host."""
        print(f"[DIAG] host recv {len(data)}B from {addr} at {time.time():.2f}: {data[:20]!r}")

        if addr in self.clients_meta:
            self._last_seen[addr] = time.time()

        if data.startswith(b'JOIN'):
            username = data.decode()[4:]

            if addr not in self.clients_meta:
                print(f"Player joined:")
                client_id = self.client_id_counter
                self.client_id_counter += 1

                self.clients_meta[addr] = {
                    "id": client_id,
                    "username": username,
                    "joined_at": time.time()
                }
            else:
                # Already registered - this is a retried JOIN (its earlier ID__ reply was likely
                # lost), not a new player. Fall through and resend the id below either way.
                client_id = self.clients_meta[addr]["id"]

            # Tell the client its id - resent on every JOIN (including retries) since we can't
            # tell whether the client is retrying because it never got this the first time.
            print(f"[DIAG] host sending ID__{client_id} back to {addr} at {time.time():.2f}")
            self.socket.sendto(b'ID__' + str(client_id).encode(), addr)

        elif data.startswith(b'DATA'):
            try:
                payload = json.loads(data[4:].decode())
            except ValueError:
                print("Corrupted packet received")
                return

            if payload.get("type") == "input":
                self.input_from_clients[addr] = payload

    def _handle_client_packet(self, data, addr):
        """Process packets received by the client."""
        print(f"[DIAG] client recv {len(data)}B from {addr} at {time.time():.2f}: {data[:20]!r}")

        if data.startswith(b'DATA'):
            try:
                payload = json.loads(data[4:].decode())
            except ValueError:
                print("Corrupted packet received")
                return

            self._last_host_packet_at = time.time()

            if payload.get("type") == "snapshot":
                self.snapshot_from_host = payload
            elif payload.get("type") == "clients":
                self.client_list = payload.get("names", [])
            elif payload.get("type") == "level_result":
                self.level_result = payload

        # Checks if hosts sends a client id
        elif data.startswith(b'ID__'):
            self.client_id = int(data[4:].decode())
            self._last_host_packet_at = time.time()



    def request_client_list(self):
        """Request the list of connected clients from the host."""
        if self.role == NetRole.CLIENT:
            self.socket.sendto(b'LIST', self.server_address)
