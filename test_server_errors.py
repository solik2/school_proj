from fastapi.testclient import TestClient
from server import app


def test_get_secret_invalid_reservation():
    client = TestClient(app)
    resp = client.get("/requests/doesnotexist", params={"requester": "foo"})
    assert resp.status_code == 404
