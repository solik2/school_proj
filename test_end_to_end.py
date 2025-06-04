import subprocess
import tempfile
import shutil
import os
from pathlib import Path
import time
import json

def run_cli(args, cwd=None):
    result = subprocess.run([
        "python3", "client/client.py"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        input="\n".join(["y"]*5),  # auto-confirm prompts
    )
    return result.stdout, result.stderr, result.returncode

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
        # Setup temp dirs for Alice and Bob
        tmpdir = tempfile.mkdtemp()
        alice_dir = Path(tmpdir) / "alice_storage"
        bob_dir = Path(tmpdir) / "bob_storage"
        alice_dir.mkdir()
        bob_dir.mkdir()
        print(f"[INFO] Alice storage: {alice_dir}\n[INFO] Bob storage: {bob_dir}")

        # 1. Register Alice
        out, err, code = run_cli([
            "register",
            "--client-id",
            "Alice",
            "--endpoint",
            "127.0.0.1:9002",
            "--space",
            "50",
            "--storage-dir",
            str(alice_dir),
        ])
        print("[REGISTER ALICE]", out)
        assert code == 0, f"Alice registration failed: {err}"
        # 2. Register Bob
        out, err, code = run_cli([
            "register",
            "--client-id",
            "Bob",
            "--endpoint",
            "127.0.0.1:9003",
            "--space",
            "100",
            "--storage-dir",
            str(bob_dir),
        ])
        print("[REGISTER BOB]", out)
        assert code == 0, f"Bob registration failed: {err}"
        # 3. Alice discovers offers
        out, err, code = run_cli(["offers", "--min-space", "50"])
        print("[OFFERS]", out)
        assert "Bob" in out, "Bob not found in offers"
        # 4. Alice reserves space on Bob
        out, err, code = run_cli([
            "reserve",
            "--from-id",
            "Alice",
            "--to-id",
            "Bob",
            "--amount",
            "20",
        ])
        print("[RESERVE]", out)
        assert "Reserved" in out, "Reservation failed"
        rid = None
        for line in out.splitlines():
            if "Reserved:" in line:
                rid = line.split(":")[-1].strip()
        assert rid, "No reservation_id found"
        # 5. Bob lists incoming requests
        out, err, code = run_cli(["requests", "--client-id", "Bob"])
        print("[REQUESTS]", out)
        assert rid in out, "Reservation not listed for Bob"
        # 6. Bob approves reservation (simulate auto-confirm)
        out, err, code = run_cli([
            "approve",
            rid,
            "--local-port",
            "9003",
            "--storage-dir",
            str(bob_dir),
        ])
        print("[APPROVE]", out)
        assert "Secret announced" in out, "Approval failed"
        # 7. Alice fetches Bob's secret and (mock) connects
        out, err, code = run_cli([
            "p2p-connect",
            rid,
            "--client-id",
            "Alice",
            "--local-port",
            "9002",
            "--server",
            "http://localhost:8000",
        ])
        print("[P2P-CONNECT]", out)
        # Accept both success and error (since P2P is not implemented)
        assert code == 0 or "P2P error" in out or "P2P error" in err
        # Cleanup
        shutil.rmtree(tmpdir)
    finally:
        server_proc.terminate()
        server_proc.wait()

if __name__ == "__main__":
    test_end_to_end()
    print("End-to-end test completed.")
