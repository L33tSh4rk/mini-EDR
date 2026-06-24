# enrollment: http post de registro do agente no servidor (inicial e periodico)

import asyncio
import json
import urllib.error
import urllib.request

from agent.core import config


def _post(url, body):
    # dispara o http post sincrono usando urllib da stdlib
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status


async def _register_once(state):
    # tenta registrar uma vez; retorna true em sucesso, false em falha
    url = f"http://{config.SERVER_HOST}:{config.SERVER_HTTP_PORT}/register"
    body = {
        "agent_id": state.agent_id,
        "ip_address": state.ip_address,
        "hostname": state.hostname,
    }
    loop = asyncio.get_running_loop()
    try:
        # roda o post bloqueante fora do event loop
        await loop.run_in_executor(None, _post, url, body)
        return True
    except (urllib.error.URLError, OSError):
        return False


async def enroll_agent(state):
    # registro inicial: insiste com backoff exponencial ate o servidor confirmar
    backoff = 1
    while True:
        if await _register_once(state):
            print(f"[enroll] agente registrado: {state.agent_id}")
            return
        print(f"[enroll] servidor indisponivel, retry em {backoff}s")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, config.MAX_BACKOFF)


async def periodic_reenroll(state):
    # re-registra periodicamente: o registry do servidor e in-memory, entao isso
    # re-anuncia o agente apos um restart do servidor (evita ficar invisivel)
    while True:
        await asyncio.sleep(config.REENROLL_INTERVAL)
        await _register_once(state)
