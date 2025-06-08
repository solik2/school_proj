# Consolidated client utilities for the P2P demo project.
# This merges the previous api_client, p2p, p2p_ops, storage, models,
# and structure modules into a single file to keep the project small
# while staying under the 600-700 line guideline.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, BinaryIO, Tuple
import os
import socket
import base64
import hashlib
import httpx

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization


# ---------------------------------------------------------------------------
# API helpers (previously api_client.py)
# ---------------------------------------------------------------------------

async def report_usage(from_id: str, to_id: str, bytes_sent: int, server: str) -> Any:
    async with httpx.AsyncClient() as client:
        payload = {"from_id": from_id, "to_id": to_id, "bytes_sent": bytes_sent}
        response = await client.post(f"{server}/report", json=payload)
        response.raise_for_status()
        return response.json()


def register(client_id: str, endpoint: str, space: int, server: str) -> Any:
    payload = {"id": client_id, "endpoint": endpoint, "available_space": space}
    response = httpx.post(f"{server}/register", json=payload)
    response.raise_for_status()
    return response.json()


def list_offers(min_space: int, server: str) -> Any:
    response = httpx.get(f"{server}/offers", params={"min_space": min_space})
    response.raise_for_status()
    return response.json()


def reserve(from_id: str, to_id: str, amount: int, server: str) -> Any:
    payload = {"from_id": from_id, "to_id": to_id, "amount": amount}
    response = httpx.post(f"{server}/reserve", json=payload)
    response.raise_for_status()
    return response.json()


def list_requests(client_id: str, server: str) -> Any:
    response = httpx.get(f"{server}/requests", params={"for": client_id})
    response.raise_for_status()
    return response.json()


def approve_reservation(reservation_id: str, secret_data: dict, server: str) -> Any:
    response = httpx.post(
        f"{server}/requests/{reservation_id}/approve",
        json={"secret_info": secret_data},
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Minimal storage utilities (previously storage.py)
# ---------------------------------------------------------------------------


def ensure_storage_dir(storage_dir: Path) -> None:
    storage_dir.mkdir(parents=True, exist_ok=True)


def validate_file_path(file_path: Path) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")


# ---------------------------------------------------------------------------
# Connection models (previously models.py and structure.py)
# ---------------------------------------------------------------------------


class ICECandidate:
    """Simple structure for an ICE candidate."""

    def __init__(self, foundation: str, component: int, protocol: str, priority: int,
                 ip: str, port: int, cand_type: str) -> None:
        self.foundation = foundation
        self.component = component
        self.protocol = protocol
        self.priority = priority
        self.ip = ip
        self.port = port
        self.type = cand_type


class SecretInfo:
    """Connection secret information."""

    def __init__(
        self,
        local_endpoint: str,
        public_endpoint: str,
        public_ip: str,
        tcp_port: int,
        connection_key: str,
        ice_candidates: Optional[List[ICECandidate]] | None = None,
        offer_sdp: Optional[str] | None = None,
    ) -> None:
        self.local_endpoint = local_endpoint
        self.public_endpoint = public_endpoint
        self.public_ip = public_ip
        self.tcp_port = tcp_port
        self.connection_key = connection_key
        self.ice_candidates = ice_candidates or []
        self.offer_sdp = offer_sdp


SecretData = {
    "peer_id": "...",
    "public_key": "...",
    "local_endpoint": "ip:port",
    "public_endpoint": "ext_ip:port",
    "ice_candidates": [],
    "offer_sdp": "...",
    "connection_key": "...",
    "signature": "...",
}


# ---------------------------------------------------------------------------
# NAT traversal and P2P utilities (previously p2p.py and p2p_ops.py)
# ---------------------------------------------------------------------------


class NATTraversal:
    def __init__(self, local_port: int) -> None:
        self.local_port = local_port
        import upnpy

        self.upnp = upnpy.UPnP()

    def setup_upnp(self) -> Optional[str]:
        try:
            device = self.upnp.discover()[0]
            service = device["WANIPConnection"]
            service.AddPortMapping(
                NewRemoteHost="",
                NewExternalPort=self.local_port,
                NewProtocol="UDP",
                NewInternalPort=self.local_port,
                NewInternalClient=self._get_local_ip(),
                NewEnabled="1",
                NewPortMappingDescription="P2P Application",
                NewLeaseDuration=0,
            )
            return service.GetExternalIPAddress()
        except Exception as e:  # pragma: no cover - best effort logging
            print(f"UPnP setup failed: {e}")
            return None

    def _get_local_ip(self) -> str:
        return socket.gethostbyname(socket.gethostname())

    def get_stun_info(self) -> Tuple[str, int]:
        import stun

        try:
            nat_type, external_ip, external_port = stun.get_ip_info()
            return external_ip, external_port
        except Exception as e:  # pragma: no cover - best effort logging
            print(f"STUN failed: {e}")
            local_ip = self._get_local_ip()
            return local_ip, self.local_port


def load_or_create_keypair(keyfile: str = ".peer_private_key") -> Tuple[
    Ed25519PrivateKey, str, str
]:
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


def get_secret_data(local_port: int) -> Dict[str, Any]:
    """Generate connection secret data for NAT traversal."""

    nat = NATTraversal(local_port)
    private_key, public_key_b64, peer_id = load_or_create_keypair()

    external_ip = nat.setup_upnp()
    if not external_ip:
        try:
            external_ip, external_port = nat.get_stun_info()
        except Exception as e:  # pragma: no cover - best effort logging
            print(f"STUN failed: {e}")
            external_ip = nat._get_local_ip()
            external_port = local_port
    else:
        external_port = local_port

    local_ip = nat._get_local_ip()

    import secrets

    connection_key = base64.b64encode(secrets.token_bytes(32)).decode()
    data_to_sign = (
        f"{peer_id}|{public_key_b64}|{local_ip}:{local_port}|"
        f"{external_ip}:{external_port}|{connection_key}"
    )
    signature = base64.b64encode(private_key.sign(data_to_sign.encode())).decode()
    return {
        "peer_id": peer_id,
        "public_key": public_key_b64,
        "local_endpoint": f"{local_ip}:{local_port}",
        "public_endpoint": f"{external_ip}:{external_port}",
        "public_ip": external_ip,
        "tcp_port": external_port,
        "connection_key": connection_key,
        "ice_candidates": [],
        "offer_sdp": "",
        "signature": signature,
    }


def initialize_nat_traversal(local_port: int) -> Dict[str, str]:
    nat = NATTraversal(local_port)
    external_ip = nat.setup_upnp()
    if not external_ip:
        external_ip, external_port = nat.get_stun_info()
    else:
        external_port = local_port
    local_ip = nat._get_local_ip()
    return {
        "local_endpoint": f"{local_ip}:{local_port}",
        "public_endpoint": f"{external_ip}:{external_port}",
        "ice_candidates": [],
        "offer_sdp": "",
    }


async def fetch_peer_secret(
    reservation_id: str, requester_id: str, server: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """Fetch the peer's connection information from the server and verify signature."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server}/requests/{reservation_id}", params={"requester": requester_id}
        )
        response.raise_for_status()
        secret_info = response.json()["secret_info"]
        data_to_sign = (
            f"{secret_info['peer_id']}|{secret_info['public_key']}|"
            f"{secret_info['local_endpoint']}|{secret_info['public_endpoint']}|"
            f"{secret_info['connection_key']}"
        )
        signature = base64.b64decode(secret_info["signature"])
        public_key_bytes = base64.b64decode(secret_info["public_key"])
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature, data_to_sign.encode())
        expected_peer_id = hashlib.sha256(public_key_bytes).hexdigest()
        if expected_peer_id != secret_info["peer_id"]:
            raise Exception("Peer ID does not match public key!")
        return secret_info


class P2PConnection:
    def __init__(self, local_port: int) -> None:
        self.nat = NATTraversal(local_port)
        self.local_port = local_port
        self.socket: Optional[socket.socket] = None

    async def connect_to_peer(self, secret_data: Dict[str, Any]) -> socket.socket:
        """Establish connection to peer using their secret data."""
        try:
            host, port = secret_data["public_endpoint"].split(":")
            port = int(port)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            return self.socket
        except Exception as e:
            if self.socket:
                self.socket.close()
            raise ConnectionError(f"Failed to connect to peer: {e}")

    def send_data(self, data: BinaryIO, chunk_size: int = 8192) -> int:
        if not self.socket:
            raise ConnectionError("No active connection")
        total_sent = 0
        while True:
            chunk = data.read(chunk_size)
            if not chunk:
                break
            self.socket.sendall(chunk)
            total_sent += len(chunk)
        return total_sent

    def receive_data(self, output: BinaryIO, chunk_size: int = 8192) -> int:
        if not self.socket:
            raise ConnectionError("No active connection")
        total_received = 0
        while True:
            chunk = self.socket.recv(chunk_size)
            if not chunk:
                break
            output.write(chunk)
            total_received += len(chunk)
        return total_received

    def close(self) -> None:
        if self.socket:
            self.socket.close()
            self.socket = None


# Convenience wrappers previously in p2p_ops.py
async def p2p_receive(reservation_id: str, local_port: int, storage_dir: Path, server: str) -> Path:
    secret_data = get_secret_data(local_port)
    peer_secret = await fetch_peer_secret(reservation_id, secret_data["peer_id"], server)
    p2p = P2PConnection(local_port)
    await p2p.connect_to_peer(peer_secret)
    storage_dir.mkdir(parents=True, exist_ok=True)
    out_file = storage_dir / f"{reservation_id}.data"
    with out_file.open("wb") as f:
        p2p.receive_data(f)
    p2p.close()
    return out_file


async def p2p_connect_and_send(
    reservation_id: str,
    client_id: str,
    local_port: int,
    file_path: Optional[Path],
    server: str,
    report_usage_func,
) -> None:
    secret = await fetch_peer_secret(reservation_id, client_id, server)
    p2p = P2PConnection(local_port)
    await p2p.connect_to_peer(secret)
    if file_path:
        with file_path.open("rb") as f:
            bytes_sent = p2p.send_data(f)
            await report_usage_func(client_id, secret["peer_id"], bytes_sent, server)
    p2p.close()

