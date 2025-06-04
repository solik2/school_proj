from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="P2P Storage UI")

HTML = """<!DOCTYPE html>
<html>
<head>
    <title>P2P Storage UI</title>
</head>
<body>
    <h1>P2P Storage Client</h1>
    <section id='register'>
        <h2>Register</h2>
        <!-- TODO: registration form -->
    </section>
    <section id='offers'>
        <h2>Offers</h2>
        <!-- TODO: offers list -->
    </section>
    <section id='reserve'>
        <h2>Reserve Space</h2>
        <!-- TODO: reservation form -->
    </section>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Return the basic HTML skeleton for the UI."""
    return HTML
