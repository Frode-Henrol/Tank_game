import socket
import threading
import time
import struct

DEFAULT_PORT = 7777
BUFFER_SIZE = 1024
TICK_RATE = 60

INPUT_FORMAT = 'fff?i'  # x, y, angle, firing, inventory_count 

class NetRole:
    """Enum for network roles."""
    NONE = 0
    HOST = 1
    CLIENT = 2

class Multiplayer:
    """Handles UDP-based multiplayer networking."""

    def __init__(self):
        """Initialize socket and role tracking."""
        self.socket = None
        self.running = False
        self.role = NetRole.NONE
        self.clients = set()      # Host only
        self.server_address = None  # Client only

    def start_host(self, port=DEFAULT_PORT):
        """Start hosting a game on given port."""
        self.role = NetRole.HOST
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', port))
        self.running = True
        threading.Thread(target=self._host_loop, daemon=True).start()
        print("Hosting started")

    def start_client(self, host_ip, port=DEFAULT_PORT):
        """Join a hosted game at host_ip:port."""
        self.role = NetRole.CLIENT
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (host_ip, port)
        self.running = True
        threading.Thread(target=self._client_loop, daemon=True).start()
        self.send_join_request()
        print("Client started")

    def stop(self):
        """Stop the socket and networking threads."""
        self.running = False
        if self.socket:
            self.socket.close()
            print("Stopping socket")

    def send_join_request(self):
        """Send a join request to the server."""
        if self.role == NetRole.CLIENT:
            self.socket.sendto(b'JOIN', self.server_address)

    def send_input(self, data):
        """Send player input to the host."""
        if self.role == NetRole.CLIENT:
            self.socket.sendto(b'INPT' + data, self.server_address)

    def broadcast_data(self, data):
        """Send data updates to all connected clients."""
        if self.role == NetRole.HOST:
            for client in self.clients:
                self.socket.sendto(b'STAT' + data, client)
                
    def pack_input(self, x, y, angle, firing, inventory_count):
        """Pack input data into bytes for sending."""
        return struct.pack(INPUT_FORMAT, x, y, angle, firing, inventory_count)

    def unpack_input(self, data):
        """Unpack input bytes into structured values."""
        return struct.unpack(INPUT_FORMAT, data)

    def send_input_data(self, x, y, angle, firing, inventory_count):
        """Send structured player input to the server."""
        if self.role == NetRole.CLIENT:
            payload = self.pack_input(x, y, angle, firing, inventory_count)
            self.socket.sendto(b'INPT' + payload, self.server_address)


    def _host_loop(self):
        """Receive and handle packets as host."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                if addr not in self.clients:
                    self.clients.add(addr)
                self._handle_host_packet(data, addr)
            except:
                pass

    def _client_loop(self):
        """Receive and handle packets as client."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                self._handle_client_packet(data)
            except:
                pass

    def _handle_host_packet(self, data, addr):
        """Process packets received by the host."""
        if data.startswith(b'JOIN'):
            print(f"Client joined: {addr}")
            # Send welcome or initial state here
        elif data.startswith(b'INPT'):
            player_input = data[4:]
            # Process input, update state, broadcast new state

    def _handle_client_packet(self, data):
        """Process packets received by the client."""
        if data.startswith(b'STAT'):
            state_data = data[4:]
            # Update local game state with server state
