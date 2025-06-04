import httpx


async def report_usage(from_id, to_id, bytes_sent, server):
    async with httpx.AsyncClient() as client:
        payload = {"from_id": from_id, "to_id": to_id, "bytes_sent": bytes_sent}
        response = await client.post(f"{server}/report", json=payload)
        response.raise_for_status()
        return response.json()


def register(client_id, endpoint, space, server):
    payload = {"id": client_id, "endpoint": endpoint, "available_space": space}
    response = httpx.post(f"{server}/register", json=payload)
    response.raise_for_status()
    return response.json()


def list_offers(min_space, server):
    response = httpx.get(f"{server}/offers", params={"min_space": min_space})
    response.raise_for_status()
    return response.json()


def reserve(from_id, to_id, amount, server):
    payload = {"from_id": from_id, "to_id": to_id, "amount": amount}
    response = httpx.post(f"{server}/reserve", json=payload)
    response.raise_for_status()
    return response.json()


def list_requests(client_id, server):
    response = httpx.get(f"{server}/requests", params={"for": client_id})
    response.raise_for_status()
    return response.json()


def approve_reservation(reservation_id, secret_data, server):
    response = httpx.post(
        f"{server}/requests/{reservation_id}/approve",
        json={"secret_info": secret_data},
    )
    response.raise_for_status()
    return response.json()
