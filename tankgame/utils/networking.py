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
        self.clients_meta = {}    # Meta data
        self.client_list = []     # For client to store the list of connected clients
        self.server_address = None  # Client only
        self.client_data_test = tuple  # ONLY TEST NEED TO BE DELETED

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
        threading.Thread(target=self._client_loop, daemon=True).start()
        self.send_join_request(username)
        print("Client started")

    def stop(self):
        """Stop the socket and networking threads."""
        self.running = False
        if self.socket:
            self.clients.clear()
            self.clients_meta.clear()
            self.socket.close()
            print("Stopping socket")

    def send_join_request(self, username):
        """Send a join request to the server."""
        if self.role == NetRole.CLIENT:
            payload = username.encode()
            self.socket.sendto(b'JOIN' + payload, self.server_address)

    def send_input(self, data):
        """Send player input to the host."""
        if self.role == NetRole.CLIENT:
            self.socket.sendto(b'INPT' + data, self.server_address)

    def broadcast_data(self, data):
        """Send data updates to all connected clients."""
        if self.role == NetRole.HOST:
            for client in self.clients:
                self.socket.sendto(data, client)
                
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
            print(f"Player joined:")
            
            parts = data.decode()[4:]
            username = parts
            
            
            print(f"Addr: {addr}")
            print(f"Username: {username}")
            
            self.clients_meta[addr] = {
                "username": username,
                "joined_at": time.time()
            }
            print(f"Client joined: {username} @ {addr}")
        elif data.startswith(b'INPT'):
            player_input = data[4:]
            # Process input, update state, broadcast new state
            print(f"Host received: {player_input.decode()}")
        
        elif data.startswith(b'LIST'):
            """Send back the list of clients to the requesting client."""
            client_list = [f"{addr}: {meta['username']}" for addr, meta in self.clients_meta.items()]
            response = "\n".join(client_list).encode()
            self.socket.sendto(b'CLNT' + response, addr)
            

    def _handle_client_packet(self, data):
        """Process packets received by the client."""
        if data.startswith(b'STAT'):
            state_data = data[4:]
            # Update local game state with server state
            print(f"Client received: {state_data.decode()}")
            
            # THIS is Just a test !!!!!!!!! need to be deleted
            s = state_data.decode().split(",")
            pos = [float(s[0]), float(s[1])]
            rotation_body_angle = float(s[2])
            rotation_turret_angle = float(s[3])
            shot_fired = s[4]
            aim_pos = [float(s[5]), float(s[6])]
            
            self.client_data_test = [pos, rotation_body_angle, rotation_turret_angle, shot_fired, aim_pos]
            

            # we need to add a smart way for the states to be stored: if host/client:
            # self.game_state.update_state(decoded_message) - maybe like this with seperate file
            
        
        elif data.startswith(b'CLNT'):
            """Process the list of clients received from the host."""
            client_list_str = data[4:].decode()
            client_lobby_info = eval(client_list_str)
            self.client_list = client_lobby_info
        
    def request_client_list(self):
        """Request the list of connected clients from the host."""
        if self.role == NetRole.CLIENT:
            self.socket.sendto(b'LIST', self.server_address)
            
