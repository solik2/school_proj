"""Web UI entry module using Jinja templates."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routes import api


app = FastAPI(title="P2P Storage UI")

# Serve templates and static assets
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API endpoints defined in a separate router
app.include_router(api.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Return the base HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

