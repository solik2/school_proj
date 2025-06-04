from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

from . import api_client
from .p2p import get_secret_data
from .p2p_ops import p2p_connect_and_send

SERVER = "http://localhost:8000"

app = FastAPI(title="P2P Storage UI")

# Allow CORS for all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models (reuse from server) ---
class RegisterRequest(BaseModel):
    id: str
    endpoint: str
    available_space: int

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
    secret_info: dict

class SecretInfo(BaseModel):
    secret_info: dict

class PendingRequest(BaseModel):
    reservation_id: str
    from_id: str
    amount: int

class SendFileBody(BaseModel):
    reservation_id: str
    client_id: str
    port: int
    file_path: str


# --- HTML stays the same ---
HTML = """<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='utf-8'/>
    <title>P2P Storage UI</title>
    <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css' rel='stylesheet'>
</head>
<body class='container py-4'>
    <h1 class='mb-4'>P2P Storage Client</h1>

    <section id='register' class='mb-5'>
        <h2>Register</h2>
        <form id='registerForm' class='row g-3'>
            <div class='col-md-4'>
                <label class='form-label'>Client ID</label>
                <input type='text' class='form-control' id='regId' required>
            </div>
            <div class='col-md-4'>
                <label class='form-label'>Endpoint</label>
                <input type='text' class='form-control' id='regEndpoint' placeholder='127.0.0.1:9001' required>
            </div>
            <div class='col-md-4'>
                <label class='form-label'>Available Space (MB)</label>
                <input type='number' class='form-control' id='regSpace' required>
            </div>
            <div class='col-12'>
                <button class='btn btn-primary' type='submit'>Register</button>
                <button class='btn btn-secondary ms-2' type='button' id='unregisterBtn' style='display:none;'>Unregister</button>
            </div>
        </form>
    </section>

    <section id='offers' class='mb-5'>
        <h2>Offers</h2>
        <form id='offersForm' class='row g-3 mb-3'>
            <div class='col-md-3'>
                <label class='form-label'>Minimum Space (MB)</label>
                <input type='number' class='form-control' id='minSpace' value='0'>
            </div>
            <div class='col-md-3 align-self-end'>
                <button class='btn btn-secondary' type='submit'>Refresh</button>
            </div>
        </form>
        <ul id='offersList' class='list-group'></ul>
    </section>

    <section id='reserve' class='mb-5'>
        <h2>Reserve Space</h2>
        <form id='reserveForm' class='row g-3'>
            <div class='col-md-4'>
                <label class='form-label'>My ID</label>
                <input type='text' class='form-control' id='reserveFrom' required>
            </div>
            <div class='col-md-4'>
                <label class='form-label'>Peer</label>
                <select id='reserveTo' class='form-select' required></select>
            </div>
            <div class='col-md-4'>
                <label class='form-label'>Amount (MB)</label>
                <input type='number' class='form-control' id='reserveAmount' required>
            </div>
            <div class='col-12'>
function updateSections(id){
    const show = id !== "";
    ["offers","reserve","requests","send"].forEach(s=>{
        document.getElementById(s).style.display = show ? "" : "none";
    });
}

    updateSections(id);
                <button class='btn btn-primary' type='submit'>Reserve</button>
            </div>
        </form>
        <div id='reserveResult' class='mt-3'></div>
    </section>

    <section id='requests' class='mb-5'>
        <h2>Incoming Requests</h2>
        <form id='requestsForm' class='row g-3 mb-3'>
            <div class='col-md-3'>
                <label class='form-label'>My ID</label>
                <input type='text' class='form-control' id='requestsId' required>
            </div>
            <div class='col-md-3'>
                <label class='form-label'>Local Port</label>
                <input type='number' class='form-control' id='requestsPort' value='9001' required>
            </div>
            <div class='col-md-3 align-self-end'>
                <button class='btn btn-secondary' type='submit'>Refresh</button>
            </div>
        </form>
        <ul id='requestsList' class='list-group'></ul>
    </section>

    <section id='send' class='mb-5' style='display:none;'>
        <h2>Send File</h2>
        <form id='sendForm' class='row g-3'>
            <input type='hidden' id='sendReservationId'>
            <div class='col-md-4'>
                <label class='form-label'>My ID</label>
                <input type='text' class='form-control' id='sendFrom' required>
            </div>
            <div class='col-md-4'>
                <label class='form-label'>Local Port</label>
                <input type='number' class='form-control' id='sendPort' value='9001' required>
            </div>
            <div class='col-md-4'>
                <label class='form-label'>File Path</label>
                <input type='text' class='form-control' id='filePath' required>
            </div>
            <div class='col-12'>
                <button class='btn btn-primary' type='submit'>Send</button>
            </div>
        </form>
    </section>

<script>
const SERVER = 'http://localhost:8000';

function api(path, method='GET', body=null) {
    return fetch(SERVER + path, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: body ? JSON.stringify(body) : null
    }).then(res => {
        if (!res.ok) throw new Error('Request failed');
        return res.json();
    });
}

let clientId = localStorage.getItem('clientId') || '';
function applyClientId(id) {
    document.getElementById('regId').value = id;
    document.getElementById('reserveFrom').value = id;
    document.getElementById('requestsId').value = id;
    document.getElementById('sendFrom').value = id;
    const disabled = id !== '';
    document.getElementById('regId').disabled = disabled;
    document.getElementById('reserveFrom').disabled = disabled;
    document.getElementById('requestsId').disabled = disabled;
    document.getElementById('sendFrom').disabled = disabled;
    document.getElementById('unregisterBtn').style.display = disabled ? '' : 'none';
}

applyClientId(clientId);

document.getElementById('registerForm').addEventListener('submit', async e => {
    e.preventDefault();
    const payload = {
        id: document.getElementById('regId').value,
        endpoint: document.getElementById('regEndpoint').value,
        available_space: parseInt(document.getElementById('regSpace').value, 10)
    };
    try {
        await api('/register', 'POST', payload);
        localStorage.setItem('clientId', payload.id);
        clientId = payload.id;
        applyClientId(clientId);
        alert('Registration successful');
    } catch (err) {
        alert('Registration failed');
    }
});

document.getElementById('unregisterBtn').addEventListener('click', async () => {
    if (!clientId) return;
    await api('/unregister', 'POST', {id: clientId});
    localStorage.removeItem('clientId');
    clientId = '';
    applyClientId(clientId);
    document.getElementById('regEndpoint').value = '';
    document.getElementById('regSpace').value = '';
});

document.getElementById('offersForm').addEventListener('submit', async e => {
    e.preventDefault();
    const minSpace = parseInt(document.getElementById('minSpace').value, 10);
    const offers = await api('/offers?min_space=' + minSpace);
    const list = document.getElementById('offersList');
    const select = document.getElementById('reserveTo');
    list.innerHTML = '';
    select.innerHTML = '';
    offers.forEach(o => {
        const item = document.createElement('li');
        item.className = 'list-group-item';
        item.textContent = o.id + ' - ' + o.free_space + ' MB';
        list.appendChild(item);

        const opt = document.createElement('option');
        opt.value = o.id;
        opt.textContent = o.id + ' (' + o.free_space + ' MB)';
        select.appendChild(opt);
    });
});

document.getElementById('reserveForm').addEventListener('submit', async e => {
    e.preventDefault();
    const payload = {
        from_id: clientId,
        to_id: document.getElementById('reserveTo').value,
        amount: parseInt(document.getElementById('reserveAmount').value, 10)
    };
    const result = await api('/reserve', 'POST', payload);
    document.getElementById('reserveResult').textContent = 'Reservation ID: ' + result.reservation_id;
    const rid = result.reservation_id;
    const fromId = clientId;
    const sendSection = document.getElementById('send');
    document.getElementById('sendReservationId').value = rid;
    document.getElementById('sendFrom').value = fromId;
    const check = async () => {
        try {
            await api('/requests/' + rid + '?requester=' + fromId);
            clearInterval(timer);
            sendSection.style.display = '';
            document.getElementById('reserveResult').textContent += ' - approved';
        } catch {}
    };
    const timer = setInterval(check, 3000);
});

document.getElementById('requestsForm').addEventListener('submit', async e => {
    e.preventDefault();
    const id = clientId;
    const port = parseInt(document.getElementById('requestsPort').value, 10);
    const list = document.getElementById('requestsList');
    const reqs = await api('/requests?for=' + id);
    list.innerHTML = '';
    reqs.forEach(r => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.textContent = r.reservation_id + ' from ' + r.from_id + ' (' + r.amount + ' MB)';
        const btn = document.createElement('button');
        btn.className = 'btn btn-sm btn-primary ms-2';
        btn.textContent = 'Approve';
        btn.onclick = async () => {
            btn.disabled = true;
            // Call a new endpoint on your UI FastAPI app to get the secret data for the port
            const secret = await api('/get_secret_data?port=' + port);
            await api('/requests/' + r.reservation_id + '/approve', 'POST', {secret_info: secret});
            li.textContent += ' - approved';
        };
        li.appendChild(btn);
        list.appendChild(li);
    });
});

document.getElementById('sendForm').addEventListener('submit', async e => {
    e.preventDefault();
    const body = {
        reservation_id: document.getElementById('sendReservationId').value,
        client_id: clientId,
        port: parseInt(document.getElementById('sendPort').value, 10),
        file_path: document.getElementById('filePath').value
    };
    await fetch('/send_file', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    alert('Send initiated');
});
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Return the basic HTML skeleton for the UI."""
    return HTML


@app.post("/register")
async def register(req: RegisterRequest):
    """Register a new client."""
    return api_client.register(req, SERVER)


@app.post("/unregister")
async def unregister(req: UnregisterRequest):
    """Unregister an existing client."""
    return api_client.unregister(req, SERVER)


@app.get("/offers", response_model=list[Offer])
async def offers(min_space: int = 0):
    """Get a list of available offers."""
    return api_client.get_offers(min_space, SERVER)


@app.post("/reserve")
async def reserve(req: ReserveRequest):
    """Reserve space from a peer."""
    return api_client.reserve(req, SERVER)


@app.get("/requests")
async def get_requests(for_peer: str):
    """Get incoming requests for approval."""
    return api_client.get_requests(for_peer, SERVER)


@app.post("/requests/{reservation_id}/approve")
async def approve_request(reservation_id: str, req: ApprovalRequest):
    """Approve a pending request."""
    return api_client.approve_request(reservation_id, req, SERVER)


@app.get("/requests/{reservation_id}")
async def get_secret(reservation_id: str, requester: str):
    """Get the secret information for a reservation."""
    return api_client.get_secret(reservation_id, requester, SERVER)


@app.post("/send_file")
async def send_file(body: SendFileBody):
    """Send a file to the peer once the reservation is approved."""
    file_path = Path(body.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    await p2p_connect_and_send(
        body.reservation_id,
        body.client_id,
        body.port,
        file_path,
        SERVER,
        api_client.report_usage,
    )
    return {"status": "sent"}

@app.get("/get_secret_data")
async def get_secret_data_endpoint(port: int):
    return get_secret_data(port)