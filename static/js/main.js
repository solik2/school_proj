const SERVER = "http://localhost:8000";

async function api(path, method = 'GET', body = null) {
    try {
        const res = await fetch(SERVER + path, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : null,
        });
        if (!res.ok) throw new Error('Request failed');
        return await res.json();
    } catch (err) {
        alert('Network error');
        throw err;
    }
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
    const rid = result.reservation_id;
    const fromId = payload.from_id;
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
    const id = document.getElementById('requestsId').value;
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
            await fetch('/approve', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({reservation_id: r.reservation_id, port})});
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
        client_id: document.getElementById('sendFrom').value,
        port: parseInt(document.getElementById('sendPort').value, 10),
        file_path: document.getElementById('filePath').value
    };
    await fetch('/send_file', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    alert('Send initiated');
});
