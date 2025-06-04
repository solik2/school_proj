from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="P2P Storage UI")

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
                <button class='btn btn-primary' type='submit'>Reserve</button>
            </div>
        </form>
        <div id='reserveResult' class='mt-3'></div>
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

document.getElementById('registerForm').addEventListener('submit', async e => {
    e.preventDefault();
    const payload = {
        id: document.getElementById('regId').value,
        endpoint: document.getElementById('regEndpoint').value,
        available_space: parseInt(document.getElementById('regSpace').value, 10)
    };
    try {
        await api('/register', 'POST', payload);
        alert('Registration successful');
    } catch (err) {
        alert('Registration failed');
    }
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
        from_id: document.getElementById('reserveFrom').value,
        to_id: document.getElementById('reserveTo').value,
        amount: parseInt(document.getElementById('reserveAmount').value, 10)
    };
    const result = await api('/reserve', 'POST', payload);
    document.getElementById('reserveResult').textContent = 'Reservation ID: ' + result.reservation_id;
});
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Return the basic HTML skeleton for the UI."""
    return HTML
