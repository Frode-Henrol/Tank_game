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

        # Disconnect detection (mid-game, after the join handshake is done)
        self._last_seen = {}         # Host: addr -> time.time() of the last packet received from that client
        self._last_host_packet_at = None  # Client: time.time() of the last packet received from the host


    def start_host(self, username, port=DEFAULT_PORT):
        """Start hosting a game on given port."""
        self.role = NetRole.HOST
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', port))
        self.running = True
        threading.Thread(target=self._host_loop, daemon=True).start()
        print("Hosting started")

    def start_client(self, host_ip, username, port=DEFAULT_PORT):
        """Join a hosted game at host_ip:port."""
        self.role = NetRole.CLIENT
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (host_ip, port)
        self.running = True
        self.client_id = 0
        self.connection_failed = False
        self._join_username = username
        self._connect_started_at = time.time()
        self._last_join_sent_at = self._connect_started_at
        threading.Thread(target=self._client_loop, daemon=True).start()
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
        """Stop the socket and networking threads."""
        self.running = False
        if self.socket:
            self.input_from_clients.clear()
            self.clients_meta.clear()
            self._last_seen.clear()
            self.socket.close()
            print("Stopping socket")

    def send_join_request(self, username):
        """Send a join request to the server."""
        if self.role == NetRole.CLIENT:
            payload = username.encode()
            self.socket.sendto(b'JOIN' + payload, self.server_address)

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
        for addr, meta in self.clients_meta.items():
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
