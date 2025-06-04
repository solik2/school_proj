import upnpy
import stun
import httpx
import socket
from typing import Dict, List, Optional, Tuple, BinaryIO
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import hashlib

class NATTraversal:
    def __init__(self, local_port: int):
        self.local_port = local_port
        self.upnp = upnpy.UPnP()
        
    def setup_upnp(self) -> Optional[str]:
        try:
            device = self.upnp.discover()[0]
            service = device['WANIPConnection']
            service.AddPortMapping(
                NewRemoteHost='',
                NewExternalPort=self.local_port,
                NewProtocol='UDP',
                NewInternalPort=self.local_port,
                NewInternalClient=self._get_local_ip(),
                NewEnabled='1',
                NewPortMappingDescription='P2P Application',
                NewLeaseDuration=0
            )
            return service.GetExternalIPAddress()
        except Exception as e:
            print(f"UPnP setup failed: {e}")
            return None

    def _get_local_ip(self) -> str:
        import socket
        return socket.gethostbyname(socket.gethostname())

    def get_stun_info(self) -> tuple:
        try:
            nat_type, external_ip, external_port = stun.get_ip_info()
            return external_ip, external_port
        except Exception as e:
            print(f"STUN failed: {e}")
            # Fallback to local interface if STUN is unavailable
            local_ip = self._get_local_ip()
            return local_ip, self.local_port

SecretData = {
    "local_endpoint": "ip:port",      # the peer's listening address
    "public_endpoint": "ext_ip:port", # from STUN
    "ice_candidates": [],             # full ICE candidate list if using TURN
    "offer_sdp": "",                  # optional WebRTC offer
}

def load_or_create_keypair(keyfile: str = ".peer_private_key"):
    """Load Ed25519 keypair from file, or create and save if not exists."""
    if os.path.exists(keyfile):
        with open(keyfile, "rb") as f:
            private_bytes = f.read()
            private_key = serialization.load_pem_private_key(private_bytes, password=None)
    else:
        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(keyfile, "wb") as f:
            f.write(private_bytes)
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    peer_id = hashlib.sha256(public_bytes).hexdigest()
    return private_key, base64.b64encode(public_bytes).decode(), peer_id

def get_secret_data(local_port: int) -> dict:
    """Get connection secret data for NAT traversal, with secure keypair."""
    nat = NATTraversal(local_port)
    private_key, public_key_b64, peer_id = load_or_create_keypair()
    
    # Try UPnP first
    external_ip = nat.setup_upnp()
    
    # If UPnP fails, use STUN
    if not external_ip:
        external_ip, external_port = nat.get_stun_info()
    else:
        external_port = local_port
        
    local_ip = nat._get_local_ip()
    
    import secrets
    connection_key = base64.b64encode(secrets.token_bytes(32)).decode()
    # Prepare the data to be signed (all fields except signature)
    data_to_sign = f"{peer_id}|{public_key_b64}|{local_ip}:{local_port}|{external_ip}:{external_port}|{connection_key}"
    signature = base64.b64encode(private_key.sign(data_to_sign.encode())).decode()
    return {
        "peer_id": peer_id,
        "public_key": public_key_b64,
        "local_endpoint": f"{local_ip}:{local_port}",
        "public_endpoint": f"{external_ip}:{external_port}",
        "public_ip": external_ip,
        "tcp_port": external_port,
        "connection_key": connection_key,
        # Placeholders for future fields:
        "ice_candidates": [],
        "offer_sdp": "",
        "signature": signature,
    }

def initialize_nat_traversal(local_port: int) -> Dict:
    nat = NATTraversal(local_port)
    
    # Try UPnP first
    external_ip = nat.setup_upnp()
    
    # If UPnP fails, use STUN
    if not external_ip:
        external_ip, external_port = nat.get_stun_info()
    else:
        external_port = local_port
        
    local_ip = nat._get_local_ip()
    
    return {
        "local_endpoint": f"{local_ip}:{local_port}",
        "public_endpoint": f"{external_ip}:{external_port}",
        "ice_candidates": [],  # Will be populated when using WebRTC/TURN
        "offer_sdp": ""
    }


async def fetch_peer_secret(reservation_id: str, requester_id: str, server: str = "http://localhost:8000") -> Dict:
    """Fetch the peer's connection information from the server and verify signature."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server}/requests/{reservation_id}",
            params={"requester": requester_id}
        )
        response.raise_for_status()
        secret_info = response.json()["secret_info"]
        # Verify signature
        data_to_sign = f"{secret_info['peer_id']}|{secret_info['public_key']}|{secret_info['local_endpoint']}|{secret_info['public_endpoint']}|{secret_info['connection_key']}"
        signature = base64.b64decode(secret_info['signature'])
        public_key_bytes = base64.b64decode(secret_info['public_key'])
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature, data_to_sign.encode())
        expected_peer_id = hashlib.sha256(public_key_bytes).hexdigest()
        if expected_peer_id != secret_info['peer_id']:
            raise Exception("Peer ID does not match public key!")
        return secret_info

class P2PConnection:
    def __init__(self, local_port: int):
        self.nat = NATTraversal(local_port)
        self.local_port = local_port
        self.socket = None

    async def connect_to_peer(self, secret_data: Dict) -> socket.socket:
        """Establish connection to peer using their secret data"""
        try:
            peer_endpoint = secret_data["public_endpoint"]
            host, port = peer_endpoint.split(":")
            port = int(port)

            # Create TCP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            return self.socket

        except Exception as e:
            if self.socket:
                self.socket.close()
            raise ConnectionError(f"Failed to connect to peer: {e}")

    def send_data(self, data: BinaryIO, chunk_size: int = 8192) -> int:
        """Stream data over the established connection"""
        if not self.socket:
            raise ConnectionError("No active connection")
        
        total_sent = 0
        try:
            while True:
                chunk = data.read(chunk_size)
                if not chunk:
                    break
                self.socket.sendall(chunk)
                total_sent += len(chunk)
            return total_sent

        except Exception as e:
            raise ConnectionError(f"Error sending data: {e}")

    def receive_data(self, output: BinaryIO, chunk_size: int = 8192) -> int:
        """Receive streaming data from the connection"""
        if not self.socket:
            raise ConnectionError("No active connection")
        
        total_received = 0
        try:
            while True:
                chunk = self.socket.recv(chunk_size)
                if not chunk:
                    break
                output.write(chunk)
                total_received += len(chunk)
            return total_received

        except Exception as e:
            raise ConnectionError(f"Error receiving data: {e}")

    def close(self):
        """Close the connection"""
        if self.socket:
            self.socket.close()
            self.socket = None

# Example usage functions
async def send_file_to_peer(
    reservation_id: str,
    requester_id: str,
    file_path: str,
    local_port: int = 12345
) -> int:
    """Helper function to send a file to a peer"""
    try:
        # Get peer connection info
        secret_data = await fetch_peer_secret(reservation_id, requester_id)
        
        # Initialize connection
        p2p = P2PConnection(local_port)
        await p2p.connect_to_peer(secret_data)
        
        # Send the file
        with open(file_path, 'rb') as f:
            bytes_sent = p2p.send_data(f)
            
        p2p.close()
        return bytes_sent
        
    except Exception as e:
        raise Exception(f"Failed to send file: {e}")

async def receive_file_from_peer(
    output_path: str,
    local_port: int = 12345
) -> int:
    """Helper function to receive a file from a peer"""
    try:
        p2p = P2PConnection(local_port)
        
        with open(output_path, 'wb') as f:
            bytes_received = p2p.receive_data(f)
            
        p2p.close()
        return bytes_received
        
    except Exception as e:
        raise Exception(f"Failed to receive file: {e}")