# rota http de enrollment dos agentes

from fastapi import APIRouter, Request

from server.api import frames
from server.schemas.models import EnrollRequest

router = APIRouter()


@router.post("/register")
async def route_register_agent(payload: EnrollRequest, request: Request):
    # registra o agente no estado e notifica os dashboards do novo agente
    registry = request.app.state.registry
    manager = request.app.state.manager
    agent = registry.register(payload.agent_id, payload.ip_address, payload.hostname)
    await manager.broadcast(frames.status_frame(agent))
    return {"status": "registered", "agent_id": payload.agent_id}
