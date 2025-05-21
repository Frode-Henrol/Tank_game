import socket
import threading
import time
import struct
import traceback

from tankgame.utils.struct_packing import pack_all_tanks, unpack_all_tanks

DEFAULT_PORT = 7777
BUFFER_SIZE = 1024

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
        self.clients_meta = {}    # Meta data for clients
        self.client_list = []     # For client to store the list of connected clients
        self.server_address = None  # Client only
        
        self.tank_data_from_host = None # Store data if client
        self.tank_data_from_clients = {}  # For host. Store client dict with addr -> tank data 
        
        self.client_id_counter = 1  
        self.client_id = 0


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
            self.tank_data_from_clients.clear()
            self.clients_meta.clear()
            self.socket.close()
            print("Stopping socket")

    def send_join_request(self, username):
        """Send a join request to the server."""
        if self.role == NetRole.CLIENT:
            payload = username.encode()
            self.socket.sendto(b'JOIN' + payload, self.server_address)

    def client_to_host_send(self, data, raw=False, prefix = b'DATA'):
        """Send client data to the host, optionally unstructured."""
        if self.role == NetRole.CLIENT:
            payload = data if raw else pack_all_tanks(data)
            prefix = "" if raw else prefix
            self.socket.sendto(prefix + payload, self.server_address)

    def host_to_clients_send(self, data, raw=False, prefix = b'DATA'):
        """Broadcast to all clients, optionally unstructured."""
        if self.role == NetRole.HOST:
            payload = data if raw else pack_all_tanks(data)
            prefix = prefix if raw else prefix
            for client_addr in list(self.clients_meta.keys()):
                self.socket.sendto(prefix + payload, client_addr)

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

    def _handle_host_packet(self, data, addr):
        """Process packets received by the host."""
        if data.startswith(b'JOIN'):
            print(f"Player joined:")
            
            username = data.decode()[4:]
            
            if addr not in self.clients_meta and data.startswith(b'JOIN'):
                client_id = self.client_id_counter
                self.client_id_counter += 1

                self.clients_meta[addr] = {
                    "id": client_id,
                    "username": username,
                    "joined_at": time.time()
                }

                # Client of its ID
                self.socket.sendto(b'ID__' + str(client_id).encode(), addr)
            
        elif data.startswith(b'DATA'):
            client_data = data[4:]
            try:
                unpacked = unpack_all_tanks(client_data)
                self.tank_data_from_clients[addr] = unpacked
            except struct.error:
                print("Corrupted packet received")
        
        # elif data.startswith(b'LIST'):
        #     """Send back the list of clients to the requesting client."""
        #     client_list = [f"{addr}: {meta['username']}" for addr, meta in self.clients_meta.items()]
        #     response = "\n".join(client_list).encode()
        #     self.socket.sendto(b'CLNT' + response, addr)
            

    def _handle_client_packet(self, data, addr):
        """Process packets received by the client."""
        # Check for unit data from host
        #print(f"data: {data[4:]}")
        if data.startswith(b'DATA'):
            #print("Client: Received data")
            host_data = data[4:]
        
            # Unpack data from the host.
            self.tank_data_from_host = unpack_all_tanks(host_data)
        
        # Check for list of clients received from the host
        elif data.startswith(b'CLNT'):
            client_list_str = data[4:].decode()
            client_lobby_info = eval(client_list_str)
            self.client_list = client_lobby_info
        
        # Checks if hosts sends a client id
        elif data.startswith(b'ID__'):
            self.client_id = int(data[4:].decode())

            
        
    def request_client_list(self):
        """Request the list of connected clients from the host."""
        if self.role == NetRole.CLIENT:
            self.socket.sendto(b'LIST', self.server_address)
            
