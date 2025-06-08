"""API routes for the web UI."""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import core
from ..core import get_secret_data, p2p_connect_and_send


SERVER = "http://localhost:8000"

router = APIRouter()


class ApproveBody(BaseModel):
    reservation_id: str
    port: int


class SendFileBody(BaseModel):
    reservation_id: str
    client_id: str
    port: int
    file_path: str


def _validate_path(path_str: str) -> Path:
    path = Path(path_str)
    if ".." in path.parts:
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return path


@router.post("/approve")
async def approve(body: ApproveBody) -> dict:
    """Approve a reservation and send our connection secret."""
    secret = get_secret_data(body.port)
    core.approve_reservation(body.reservation_id, secret, SERVER)
    return {"status": "approved"}


@router.post("/send_file")
async def send_file(body: SendFileBody) -> dict:
    """Send a file to the peer once the reservation is approved."""
    file_path = _validate_path(body.file_path)
    await p2p_connect_and_send(
        body.reservation_id,
        body.client_id,
        body.port,
        file_path,
        SERVER,
        core.report_usage,
    )
    return {"status": "sent"}

