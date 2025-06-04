import asyncio
import socket
import threading
from pathlib import Path
from unittest.mock import AsyncMock, patch

import sys
from pathlib import Path as _Path

# Mimic running client scripts directly by adding the client directory to sys.path
CLIENT_DIR = _Path(__file__).resolve().parent / "client"
if str(CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(CLIENT_DIR))

from p2p_ops import p2p_receive


def _start_sender(port: int, data: bytes) -> None:
    """Start a simple TCP server that sends `data` and closes."""

    def _run(server_sock: socket.socket) -> None:
        conn, _ = server_sock.accept()
        conn.sendall(data)
        conn.close()
        server_sock.close()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    threading.Thread(target=_run, args=(srv,), daemon=True).start()


def test_p2p_receive_saves_file(tmp_path: Path) -> None:
    test_data = b"hello world"

    # Prepare a local TCP server to act as the peer sending data
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.listen(1)

    def serve() -> None:
        conn, _ = sock.accept()
        conn.sendall(test_data)
        conn.close()
        sock.close()

    threading.Thread(target=serve, daemon=True).start()

    async def run() -> None:
        with patch(
            "p2p_ops.get_secret_data", return_value={"peer_id": "peerA"}
        ), patch(
            "p2p_ops.fetch_peer_secret",
            new=AsyncMock(
                return_value={"public_endpoint": f"127.0.0.1:{port}"}
            ),
        ):
            await p2p_receive("res123", 12345, tmp_path, "http://server")

    asyncio.run(run())

    out_file = tmp_path / "res123.bin"
    assert out_file.exists()
    assert out_file.read_bytes() == test_data

