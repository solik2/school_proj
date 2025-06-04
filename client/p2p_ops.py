import asyncio
from p2p import P2PConnection, fetch_peer_secret, get_secret_data

async def p2p_receive(reservation_id, local_port, storage_dir, server):
    secret_data = get_secret_data(local_port)

    # Fetch peer secret (blocking for now)
    peer_secret = await fetch_peer_secret(reservation_id, secret_data["peer_id"], server)

    p2p = P2PConnection(local_port)
    await p2p.connect_to_peer(peer_secret)
    # TODO: implement file-receiving logic here
    p2p.close()

async def p2p_connect_and_send(reservation_id, client_id, local_port, file_path, server, report_usage_func):
    secret = await fetch_peer_secret(reservation_id, client_id, server)
    p2p = P2PConnection(local_port)
    await p2p.connect_to_peer(secret)
    if file_path:
        with file_path.open("rb") as f:
            bytes_sent = p2p.send_data(f)
            await report_usage_func(client_id, secret["peer_id"], bytes_sent, server)
    p2p.close()
