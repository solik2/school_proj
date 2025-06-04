import subprocess
import tempfile
import shutil
import os
from pathlib import Path
import time
import asyncio

from client import api_client
from client.p2p import get_secret_data
from client.p2p_ops import p2p_connect_and_send

SERVER_URL = "http://localhost:8000"


def test_end_to_end():
    # Start API server
    if os.path.exists("clients.json"):
        os.remove("clients.json")
    server_proc = subprocess.Popen(
        ["python3", "-m", "uvicorn", "server:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(1)
    try:
        tmpdir = tempfile.mkdtemp()
        alice_dir = Path(tmpdir) / "alice_storage"
        bob_dir = Path(tmpdir) / "bob_storage"
        alice_dir.mkdir()
        bob_dir.mkdir()

        # 1. Register Alice and Bob
        api_client.register("Alice", "127.0.0.1:9002", 50, SERVER_URL)
        api_client.register("Bob", "127.0.0.1:9003", 100, SERVER_URL)

        # 2. Alice discovers offers
        offers = api_client.list_offers(50, SERVER_URL)
        assert any(o["id"] == "Bob" for o in offers)

        # 3. Alice reserves space on Bob
        reserve_result = api_client.reserve("Alice", "Bob", 20, SERVER_URL)
        rid = reserve_result["reservation_id"]

        # 4. Bob sees the request and approves it
        requests_ = api_client.list_requests("Bob", SERVER_URL)
        assert any(r["reservation_id"] == rid for r in requests_)
        secret_data = get_secret_data(9003)
        api_client.approve_reservation(rid, secret_data, SERVER_URL)

        # 5. Alice fetches Bob's secret and (mock) connects
        async def run() -> None:
            try:
                await p2p_connect_and_send(
                    rid, "Alice", 9002, None, SERVER_URL, api_client.report_usage
                )
            except Exception:
                # Connection is expected to fail in this skeleton
                pass

        asyncio.run(run())
    finally:
        shutil.rmtree(tmpdir)
        server_proc.terminate()
        server_proc.wait()


if __name__ == "__main__":
    test_end_to_end()
    print("End-to-end test completed.")
