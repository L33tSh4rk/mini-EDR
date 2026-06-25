# entrypoint da api do servidor mini-edr (fastapi + tasks de background)

import asyncio
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from server import config
from server.api.alerts import listen_worker_alerts
from server.api.connections import ConnectionManager
from server.api.dashboard_ws import router as dashboard_router
from server.api.enrollment import router as enrollment_router
from server.api.heartbeat import listen_udp_heartbeats
from server.api.reaper import reap_offline_agents
from server.api.alert_store import AlertStore
from server.api.registry import AgentRegistry
from server.api.web import mount_static
from server.api.web import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # inicializa estado compartilhado e sobe tasks de background
    app.state.redis = aioredis.Redis(
        host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True
    )
    app.state.registry = AgentRegistry()
    app.state.manager = ConnectionManager()
    # guarda os alertas ativos para reenvio no snapshot (sobrevivem ao refresh)
    app.state.alerts = AlertStore()

    # abre socket udp puro de heartbeats
    udp_transport, _ = await listen_udp_heartbeats(app.state.registry, app.state.manager)

    # sobe consumidor de alertas e varredor de offline
    tasks = [
        asyncio.create_task(listen_worker_alerts(app.state.redis, app.state.manager, app.state.alerts)),
        asyncio.create_task(reap_offline_agents(app.state.registry, app.state.manager)),
    ]
    try:
        yield
    finally:
        # encerra tasks, socket udp e conexao redis
        for task in tasks:
            task.cancel()
        udp_transport.close()
        await app.state.redis.aclose()


# instancia a aplicacao com o ciclo de vida gerenciado
app = FastAPI(title="mini-edr api", lifespan=lifespan)
# rota http de enrollment dos agentes
app.include_router(enrollment_router)
# rota websocket do dashboard
app.include_router(dashboard_router)
# pagina html do dashboard
app.include_router(web_router)
# arquivos estaticos (css/js) do dashboard
mount_static(app)
