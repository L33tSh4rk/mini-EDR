# rotas web do dashboard: pagina via jinja2 e arquivos estaticos

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# raiz do projeto (pai do pacote server)
BASE_DIR = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = BASE_DIR / "dashboard"

# engine de templates apontando para a pasta do dashboard
templates = Jinja2Templates(directory=str(DASHBOARD_DIR / "templates"))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def route_dashboard(request: Request):
    # serve a pagina html do dashboard
    return templates.TemplateResponse(request, "index.html")


def mount_static(app):
    # monta os arquivos estaticos (css/js) do dashboard
    app.mount(
        "/static",
        StaticFiles(directory=str(DASHBOARD_DIR / "static")),
        name="static",
    )
