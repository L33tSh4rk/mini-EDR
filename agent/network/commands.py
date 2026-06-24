# listener de comandos: escuta o canal pub/sub e despacha acoes de mitigacao

import asyncio
import json

import redis.exceptions

from agent.core import config
from agent.network import actions


async def _dispatch(state, frame):
    # interpreta o frame trigger_order e executa a acao correspondente
    if frame.get("frame_type") != "trigger_order":
        return
    data = frame.get("data", {})
    command = data.get("command")
    params = data.get("parameters") or {}
    if command == "KILL":
        # encerra o processo alvo
        pid = params.get("pid")
        ok = await actions.execute_kill(pid)
        print(f"[command] kill pid={pid} ok={ok}")
    elif command == "ISOLATE":
        # isola o host via iptables (actions loga o resultado)
        await actions.execute_isolation(state)
    elif command == "LIFT":
        # reverte o isolamento por ordem do servidor (actions loga o resultado)
        await actions.lift_isolation(state)


async def listen_commands(state, client):
    # loop que assina commands:{agent_id} e reconecta em falha
    channel = config.commands_channel(state.agent_id)
    backoff = 1
    while True:
        try:
            pubsub = client.pubsub()
            await pubsub.subscribe(channel)
            print(f"[command] inscrito em {channel}")
            backoff = 1
            # loop bloqueante consumindo mensagens do canal
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    frame = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    # frame malformado, ignora
                    continue
                try:
                    await _dispatch(state, frame)
                except Exception as exc:
                    # falha ao executar a ordem nao pode derrubar o listener
                    print(f"[command] erro ao executar ordem ({exc!r})")
        except (redis.exceptions.ConnectionError, OSError) as exc:
            # perdeu o redis: tenta reassinar com backoff
            print(f"[command] conexao perdida ({exc}), retry em {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, config.MAX_BACKOFF)
