import asyncio
import socket
from pathlib import Path

import typer

from api_client import (
    report_usage,
    register as api_register,
    list_offers as api_list_offers,
    reserve as api_reserve,
    list_requests as api_list_requests,
    approve_reservation,
)
from storage import ensure_storage_dir, validate_file_path
from p2p_ops import p2p_connect_and_send, p2p_receive
from p2p import get_secret_data

app = typer.Typer(help="Minimal P2P Storage Client")


@app.command()
def register(
    client_id: str = typer.Option(..., help="Your client ID"),
    endpoint: str = typer.Option(..., help="Your host:port"),
    space: int = typer.Option(
        None, prompt="How many MB of storage space do you want to host?"
    ),
    storage_dir: Path = typer.Option(
        ..., prompt="Which folder should host incoming files?"
    ),
    server: str = typer.Option("http://localhost:8000", help="Server URL"),
) -> None:
    """Register this peer with available storage space."""
    ensure_storage_dir(storage_dir)
    result = api_register(client_id, endpoint, space, server)
    typer.echo(f"Registered successfully: {result}")


@app.command("offers")
def list_offers(
    min_space: int = typer.Option(1, help="Minimum free space (MB)"),
    server: str = typer.Option("http://localhost:8000", help="Server URL"),
) -> None:
    """List peers offering at least `min_space` MB."""
    peers = api_list_offers(min_space, server)
    if not peers:
        typer.echo("No peers available.")
        raise typer.Exit()
    for peer in peers:
        typer.echo(
            f"Peer {peer['id']}: {peer['free_space']} MB @ {peer['endpoint']}"
        )


@app.command()
def reserve(
    from_id: str = typer.Option(..., help="Your client ID"),
    to_id: str = typer.Option(..., help="Peer ID to reserve on"),
    amount: int = typer.Option(..., help="Amount in MB to reserve"),
    server: str = typer.Option("http://localhost:8000", help="Server URL"),
) -> None:
    """Reserve space on another peer."""
    result = api_reserve(from_id, to_id, amount, server)
    reservation_id = result["reservation_id"]
    typer.echo(f"Reserved: {reservation_id}")


@app.command("requests")
def list_requests(
    client_id: str = typer.Option(..., help="Your peer ID"),
    server: str = typer.Option("http://localhost:8000", help="Server URL"),
) -> None:
    """List pending storage requests addressed to this peer."""
    requests_ = api_list_requests(client_id, server)
    if not requests_:
        typer.echo("No pending requests.")
        raise typer.Exit()
    typer.echo("Pending requests:")
    for req in requests_:
        typer.echo(
            f"- Reservation {req['reservation_id']} from {req['from_id']} "
            f"({req['amount']} MB)"
        )


@app.command()
def approve(
    reservation_id: str = typer.Argument(..., help="Reservation ID"),
    local_port: int = typer.Option(12345, help="Local port to use"),
    storage_dir: Path = typer.Option(
        ..., prompt="Folder to host incoming files"
    ),
    server: str = typer.Option("http://localhost:8000", help="Server URL"),
) -> None:
    """Approve a reservation, share secret, and start receiving files."""
    if not typer.confirm(
        f"Approve reservation {reservation_id} and share your secret data?"
    ):
        typer.echo("Reservation not approved.")
        raise typer.Abort()

    ensure_storage_dir(storage_dir)
    secret_data = get_secret_data(local_port)
    approve_reservation(reservation_id, secret_data, server)
    typer.echo("Secret announced:")
    typer.echo(secret_data)

    # Begin P2P receive
    asyncio.run(p2p_receive(reservation_id, local_port, storage_dir, server))
    typer.echo(f"P2P connection established; storing into {storage_dir}")


@app.command()
def p2p_connect(
    reservation_id: str = typer.Argument(..., help="Reservation ID"),
    client_id: str = typer.Option(..., help="Your client ID"),
    local_port: int = typer.Option(12345, help="Local port to use"),
    file_path: Path = typer.Option(
        None, help="Optional path to file to send"
    ),
    server: str = typer.Option("http://localhost:8000", help="Server URL"),
) -> None:
    """Establish a P2P connection and optionally send a file."""
    async def _run() -> None:
        if file_path:
            try:
                validate_file_path(file_path)
            except FileNotFoundError as e:
                typer.echo(str(e))
                return
        try:
            await p2p_connect_and_send(reservation_id, client_id, local_port, file_path, server, report_usage)
            typer.echo("P2P operation completed.")
        except Exception as e:
            typer.echo(f"P2P error: {e}")
            raise typer.Exit(1)

    try:
        asyncio.run(_run())
    except Exception as e:
        typer.echo(f"P2P error: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
