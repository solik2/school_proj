from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uuid
from typing import List
from fastapi import Query
import json
from pathlib import Path


app = FastAPI()


# --- Models ---
class RegisterRequest(BaseModel):
    id: str
    endpoint: str
    available_space: int  # in MB


class UnregisterRequest(BaseModel):
    id: str


class Offer(BaseModel):
    id: str
    endpoint: str
    free_space: int


class ReserveRequest(BaseModel):
    from_id: str
    to_id: str
    amount: int


class ApprovalRequest(BaseModel):
    secret_info: dict  # Raw connection info from peer (expects new format)
    # Optionally, you could add validation here for required fields


class SecretInfo(BaseModel):
    secret_info: dict  # Raw connection info to return (expects new format)


class PendingRequest(BaseModel):
    reservation_id: str
    from_id: str
    amount: int


# --- In-memory stores ---
CLIENTS_DB_PATH = Path("clients.json")


def load_clients():
    if CLIENTS_DB_PATH.exists():
        with CLIENTS_DB_PATH.open("r") as f:
            data = json.load(f)
            # Convert dicts to RegisterRequest objects
            return {
                cid: RegisterRequest(**cdata)
                for cid, cdata in data.get("clients", {}).items()
            }
    return {}


def save_clients(clients_dict):
    # Convert RegisterRequest objects to dicts
    data = {"clients": {cid: c.dict() for cid, c in clients_dict.items()}}
    with CLIENTS_DB_PATH.open("w") as f:
        json.dump(data, f, indent=2)


clients: dict[str, RegisterRequest] = load_clients()

reservations: dict[str, dict] = {}
# reservations[rid] = {
#   "from_id": str, "to_id": str, "amount": int,
#   "approved": bool, "secret_info": str|None
# }


# --- Endpoints ---
@app.post("/register", status_code=201)
def register(req: RegisterRequest):
    if req.id in clients:
        raise HTTPException(400, f"Client {req.id} already registered")
    clients[req.id] = req
    save_clients(clients)
    return {"status": "registered"}


@app.post("/unregister")
def unregister(req: UnregisterRequest):
    """Remove a client from the registry."""
    if req.id not in clients:
        raise HTTPException(404, "Client not found")
    del clients[req.id]
    save_clients(clients)
    return {"status": "unregistered"}


@app.get("/offers", response_model=List[Offer])
def list_offers(min_space: int = Query(0, description="Minimum free space in MB")):
    """
    Return all registered peers offering at least `min_space` MB.
    """
    results: List[Offer] = []
    for client in clients.values():
        if client.available_space >= min_space:
            results.append(
                Offer(
                    id=client.id,
                    endpoint=client.endpoint,
                    free_space=client.available_space,
                )
            )
    return results


@app.post("/reserve")
def reserve(req: ReserveRequest):
    peer = clients.get(req.to_id)
    if not peer:
        raise HTTPException(404, "Peer not found")
    if peer.available_space < req.amount:
        raise HTTPException(400, "Insufficient space")
    rid = uuid.uuid4().hex
    reservations[rid] = {
        "from_id": req.from_id,
        "to_id": req.to_id,
        "amount": req.amount,
        "approved": False,
        "secret_info": None,
    }
    return {"reservation_id": rid}


@app.get("/requests")
def get_requests(for_peer: str = Query(..., alias="for")):
    return [
        PendingRequest(
            reservation_id=rid,
            from_id=data["from_id"],
            amount=data["amount"],
        ).dict()
        for rid, data in reservations.items()
        if data["to_id"] == for_peer and not data["approved"]
    ]


@app.post("/requests/{reservation_id}/approve")
def approve_request(reservation_id: str, req: ApprovalRequest):
    """Store the raw connection secret info from the peer (expects new format)"""
    data = reservations.get(reservation_id)
    if not data:
        raise HTTPException(404, "Reservation not found")
    if data["approved"]:
        raise HTTPException(400, "Already approved")
    # Optionally, validate required fields in req.secret_info here
    data["approved"] = True
    # Store the raw secret_info dict without modification (expects new format)
    data["secret_info"] = req.secret_info
    return {"status": "approved"}


@app.get("/requests/{reservation_id}")
def get_secret(reservation_id: str, requester: str = Query(...)):
    """Return the raw connection secret info to the requester (expects new format)"""
    data = reservations.get(reservation_id)
    if not data or not data["approved"]:
        raise HTTPException(404, "Secret not available")
    if data["from_id"] != requester:
        raise HTTPException(403, "Not your reservation")
    # Return the raw secret_info dict without modification (expects new format)
    return SecretInfo(secret_info=data["secret_info"]).dict()
