# estado temporal de correlacao por agente no redis (ttl)

import json

from server import config

# limite de eventos guardados por agente na janela
MAX_WINDOW = 50


def _summary(event):
    # projeta o evento para o resumo guardado na janela
    p = event.payload
    return {
        "timestamp": event.timestamp,
        "event_type": event.event_type,
        "pid": p.pid,
        "process_name": p.process_name,
        "cmdline": p.cmdline,
        "user": p.user,
        "file_path": p.file_path,
        "action": p.action,
    }


async def load_state(client, agent_id):
    # le o estado do agente e tolera ausencia e formato antigo (lista pura)
    raw = await client.get(config.corr_key(agent_id))
    if not raw:
        return {"window": [], "fired": []}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"window": [], "fired": []}
    if isinstance(data, dict):
        return {"window": data.get("window", []), "fired": data.get("fired", [])}
    
    return {"window": data, "fired": []}


async def _write(client, agent_id, state):
    # reescreve estado renovando ttl (janela deslizante)
    await client.set(config.corr_key(agent_id), json.dumps(state), ex=config.CORR_TTL)


async def record_event(client, event):
    # anexa evento a janela do agente, persiste e retorna estado
    state = await load_state(client, event.agent_id)
    state["window"].append(_summary(event))
    # mantem apenas os eventos mais recentes
    state["window"] = state["window"][-MAX_WINDOW:]
    await _write(client, event.agent_id, state)
    return state


async def persist_fired(client, agent_id, state):
    # persiste estado apos marcar regras de correlacao como disparadas
    await _write(client, agent_id, state)
