from fastapi.testclient import TestClient
from client.ui import app
from unittest.mock import AsyncMock, patch


def test_send_file_bad_path():
    client = TestClient(app)
    data = {
        "reservation_id": "abc",
        "client_id": "me",
        "port": 1234,
        "file_path": "../etc/passwd",
    }
    with patch("client.routes.api.p2p_connect_and_send", new_callable=AsyncMock) as mock_send:
        resp = client.post("/send_file", json=data)
        assert resp.status_code == 400
        mock_send.assert_not_awaited()
