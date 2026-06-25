# websocket do dashboard: snapshot inicial, recepcao de ordens e mitigacao

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from server import config
from server.api import frames
from server.schemas.models import TriggerOrder

router = APIRouter()


@router.websocket("/ws")
async def route_websocket_dashboard(websocket: WebSocket):
    # canal de tempo real com o dashboard, multiplexa frames json tipados
    manager = websocket.app.state.manager
    registry = websocket.app.state.registry
    client = websocket.app.state.redis
    alerts = websocket.app.state.alerts
    await manager.connect(websocket)
    # snapshot inicial: agentes (com isolated) + alertas ativos (sobrevive ao refresh)
    await websocket.send_json(frames.agent_list_frame(registry.all()))
    await websocket.send_json(frames.alert_list_frame(alerts.all()))
    try:
        # loop de recepcao de frames vindos do dashboard
        while True:
            frame = await websocket.receive_json()
            await _dispatch(frame, client, registry, manager, alerts)
    except WebSocketDisconnect:
        # dashboard desconectou
        manager.disconnect(websocket)


async def _dispatch(frame, client, registry, manager, alerts):
    # despacha frames recebidos do dashboard conforme o tipo
    if not isinstance(frame, dict):
        return
    ft = frame.get("frame_type")
    if ft == "trigger_order":
        await route_trigger_mitigation(frame, client, registry, manager)
    elif ft == "resolve_alert":
        await route_resolve_alert(frame, alerts, manager)


async def route_resolve_alert(frame, alerts, manager):
    # remove um alerta acionado/dispensado e avisa os dashboards
    alert_id = (frame.get("data") or {}).get("alert_id")
    if alert_id and alerts.remove(alert_id) is not None:
        await manager.broadcast(frames.alert_resolved_frame(alert_id))


async def route_trigger_mitigation(frame, client, registry, manager):
    # valida a ordem, publica no canal do agente e devolve feedback aos dashboards
    try:
        order = TriggerOrder.model_validate(frame)
    except ValidationError:
        # ordem malformada, ignora
        return
    data = order.data
    # publica o frame normalizado pro agente consumir
    await client.publish(config.commands_channel(data.target_agent), json.dumps(order.model_dump()))

    # atualiza o estado de isolamento lembrado e notifica os dashboards
    if data.command == "ISOLATE":
        agent = registry.set_isolated(data.target_agent, True)
        if agent is not None:
            await manager.broadcast(frames.status_frame(agent))
    elif data.command == "LIFT":
        agent = registry.set_isolated(data.target_agent, False)
        if agent is not None:
            await manager.broadcast(frames.status_frame(agent))

    # ack do comando (feedback visual / toast no dashboard)
    pid = data.parameters.pid if data.parameters else None
    await manager.broadcast(frames.command_ack_frame(data.command, data.target_agent, pid))
